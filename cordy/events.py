from __future__ import annotations

import asyncio
import inspect
from collections.abc import Coroutine
from typing import Any, Callable, Optional, overload

# +--------+                                       +---------+
# |Emitter| --(_Subscription() event stream)-----> |Publisher| <--- (Event stream from other Emitter/Filter)
# +-------+                                        +---+---+-+
# ^ Pushing data into a Linked List of Futures         |   |^ Pulling data from list (_notify_loop)
#                                                      |   |
#        Subscriber <---(Coroutine called)-------(_notify Task) -----> Subscriber
#               |                                          |                  |
#               +<--------------------------------------(Other _notify Task)->+
#
# _notify Tasks are created for each event
# Models
#   Emitter ----(Pub/Sub-push (with implicit stream))-> Filter / Publisher
#     - Filter --> Publisher is same as above since, issubclass(Filter, Emitter) == True
#   Publisher ----(Observer pattern)--> Subcribers (aka Coroutine Funstions)

CoroFn = Callable[..., Coroutine]

class Event:
    __slots__ = ("name", "args")

    name: str
    args: tuple[Any, ...]

    def __init__(self, name, /, *args) -> None:
        self.name = name
        self.args = args

    async def run(self, coro: CoroFn) -> None:
        try:
            await coro(*self.args)
        except asyncio.CancelledError:
            pass

FilterFn = Callable[[Event], bool]

class Emitter:
    def __init__(self) -> None:
        self.loop = asyncio.get_event_loop()
        self._aiter_fut = self.loop.create_future()

    async def emit(self, event: Event) -> None:
        fut = self.loop.create_future()
        self._aiter_fut.set_result((event, fut))
        self._aiter_fut = fut

    def filter(self, func: FilterFn):
        return Filter(func, self)

    def __aiter__(self):
        return _Subscription(self._aiter_fut)

class Filter(Emitter):
    def __init__(self, filter_: FilterFn, source: Emitter) -> None:
        super().__init__()
        self.filter = filter_
        self.src = source
        asyncio.get_event_loop().create_task(self._emit_loop())

    async def _emit_loop(self) -> None:
        loop =  asyncio.get_event_loop()
        async for event in self.src:
            if self.filter(event):
                await self.emit()

class _Subscription:
    def __init__(self, fut: asyncio.Future) -> None:
        self.fut = fut

    async def __anext__(self) -> Event:
        event, self.fut = await self.fut
        return event


class Publisher:
    def __init__(self, error_hdlr: Optional[Callable[[Exception], Coroutine]] = None) -> None:
        self.waiters = dict[str, asyncio.Future]()
        self.listeners = dict[str, set[CoroFn]]()
        self.emitters = dict[Emitter, asyncio.Task]()
        self.loop = asyncio.get_event_loop()
        self.err_hdlr = error_hdlr

    async def _notify(self, event: Event) -> None:
        if event.name in self.listeners:
            for i in asyncio.as_completed([event.run(j) for j in self.listeners[event.name]]):
                try:
                    await i
                except Exception as err:
                    if self.err_hdlr is not None:
                        await self.err_hdlr(err)
                    else:
                        raise err
        if event.name in self.waiters:
            self.waiters[event.name].set_result(event.args)

    async def _notify_loop(self, emitter: Emitter) -> None:
        loop = self.loop
        try:
            async for event in emitter:
                if emitter not in self.emitters:
                    break
                loop.create_task(self._notify(event))
        except asyncio.CancelledError:
            return

    @overload
    def subscribe(self) -> Callable[[CoroFn], CoroFn]:
        ...

    @overload
    def subscribe(self, name: str) -> Callable[[CoroFn], CoroFn]:
        ...

    @overload
    def subscribe(self, name: str, func: CoroFn) -> None:
        ...

    def subscribe(self, name: Optional[str] = None, func: Optional[CoroFn] = None):
        def decorator(fn: CoroFn) -> None:
            if not inspect.iscoroutinefunction(fn):
                raise TypeError(f"Expected a coroutine function got {type(fn)}.")
            nonlocal name
            if name is None:
                name = fn.__name__
            listeners = self.listeners.get(name, None)
            if listeners is None:
                self.listeners[name] = listeners = set()
            listeners.add(fn)
            return fn

        if func is None:
            return decorator
        else:
            decorator(func)

    async def wait_for(self, event_name: str, timeout: Optional[int] = None) -> tuple[Any, ...]:
        waiter = self.waiters.get(event_name, None)
        if waiter is None:
            self.waiters[event_name] = waiter = self.loop.create_future()

        return (await asyncio.wait_for(waiter, timeout=timeout))

    def add(self, emitter: Emitter) -> None:
        task = self.emitters.get(emitter, None)
        if task is not None:
            task.cancel()
        self.emitters[emitter] = self.loop.create_task(self._notify_loop(emitter))

    def remove(self, emitter: Emitter) -> None:
        task = self.emitters.get(emitter, None)
        if task is None:
            return
        else:
            task.cancel()
            del self.emitters[emitter]

