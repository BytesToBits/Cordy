from __future__ import annotations

import asyncio
from inspect import iscoroutinefunction
from typing import Any, Callable, overload, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Coroutine

__all__ = (
    "Emitter",
    "Event",
    "Filter",
    "Publisher"
)

# +-------+                                        +---------+
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

# TODO: Make integrations with reactive data streams.

CoroFn = Callable[..., Coroutine]
CheckFn = Callable[..., bool]


def _clean_event(name: str):
    return name.casefold().removeprefix("on_")

class Event:
    __slots__ = ("name", "args")

    name: str
    args: tuple[Any, ...]

    def __init__(self, name, /, *args) -> None:
        self.name = _clean_event(name)
        self.args = args

    async def run(self, coro: CoroFn, err_hdlr: Callable[[Exception], Coroutine] = None) -> None:
        try:
            await coro(*self.args)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            if err_hdlr:
                await err_hdlr(err)
            else:
                raise err

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

    def __aiter__(self):
        return self

    async def __anext__(self) -> Event:
        event, self.fut = await self.fut
        return event

class Publisher:
    waiter: dict[str, set[tuple[asyncio.Future, CheckFn | None]]]
    listeners: dict[str, set[CoroFn]]
    emitters: dict[Emitter, asyncio.Task]

    def __init__(self, error_hdlr: Callable[[Exception], Coroutine] = None) -> None:
        self.waiters = dict()
        self.listeners = dict()
        self.emitters = dict()
        self.loop = asyncio.get_event_loop()
        self.err_hdlr = error_hdlr

    async def _notify(self, event: Event) -> None:
        in_lst = event.name in self.listeners
        if in_lst:
            aw = asyncio.gather(*(event.run(j, self.err_hdlr) for j in self.listeners[event.name]))

        if event.name in self.waiters:
            for fut, check in self.waiters[event.name]:
                if check is not None:
                    if check(*event.args):
                        fut.set_result(*event.args)
                else:
                    fut.set_result(*event.args)

        if in_lst:
            await aw

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

    def subscribe(self, name: str = None, func: CoroFn = None):
        def decorator(fn: CoroFn) -> None:
            if not iscoroutinefunction(fn):
                raise TypeError(f"Expected a coroutine function got {type(fn)}.")
            nonlocal name
            name = _clean_event(name or fn.__name__)
            listeners = self.listeners.get(name, None)
            if listeners is None:
                self.listeners[name] = listeners = set()
            listeners.add(fn)
            return fn

        if func is None:
            return decorator
        else:
            decorator(func)

    def unsubscribe(self, listener: CoroFn, name: str = None) -> None:
        ev_listeners = self.listeners.get(_clean_event(name or listener.__name__.lower()))
        try:
            if ev_listeners:
                ev_listeners.remove(listener)
        except KeyError:
            return

    async def wait_for(self, name: str, timeout: int = None, check: CheckFn = None) -> tuple[Any, ...]:
        name = _clean_event(name)
        ev_waiters = self.waiters.get(name)
        if ev_waiters is None:
            self.waiters[name] = ev_waiters = set()

        fut = self.loop.create_future()
        pair = (fut, check)
        ev_waiters.add(pair)

        try:
            ret = await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError as err:
            raise err from None
        else:
            return ret
        finally:
            ev_waiters.discard(pair)

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
