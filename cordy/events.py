from __future__ import annotations

import asyncio
import inspect
from collections.abc import Coroutine
from typing import Any, Awaitable, Callable, Optional, Union, overload

CoroFn = Callable[..., Coroutine]

class Event:
    __slots__ = ("name", "args", "kwargs")

    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    def __init__(self, name, /, *args, **kwargs) -> None:
        self.name = name
        self.args = args
        self.kwargs = kwargs

    async def run(self, coro: CoroFn) -> None:
        try:
            await coro(*self.args, **self.kwargs)
        except asyncio.CancelledError:
            pass

class Emitter:
    def __init__(self, pubs: Optional[Union[list[Publisher], Publisher]] = None) -> None:
        if isinstance(pubs, list):
            self.pubs = pubs
        else:
            self.pubs = [pubs or Publisher()]
        self.queue = []
        self._waiters = []

    async def emit(self, event: Event) -> None:
        for pub in self.pubs:
            self.pubs.publish(event)

        for fut in self._waiters:
            fut.set_result(event)

        self._waiters = []

    def __aiter__(self):
        return self

    async def __anext__(self) -> Event:
        fut = asyncio.get_event_loop().create_future()
        self._waiters.append(fut)
        return await fut


class Publisher:
    def __init__(self) -> None:
        self.listeners = dict[str, list[CoroFn]]()

    async def notify(self, event: Event):
        for i in asyncio.as_completed([event.run(j) for j in self.listeners[event.name]]):
            await i # breakpoint

    @overload
    def subscribe(self, name: str) -> Callable[[CoroFn], None]:
        ...

    @overload
    def subscribe(self, name: str, func: CoroFn) -> None:
        ...

    @overload
    def subscribe(self, name: str, func: None) -> Callable[[CoroFn], None]:
        ...

    def subscribe(self, name: Optional[str] = None, func: Optional[CoroFn] = None):
        def decorator(fn: CoroFn) -> None:
            if not inspect.iscoroutinefunction(fn):
                raise TypeError(f"Expected a coroutine function got {type(fn)}.")
            nonlocal name
            if name is None:
                name = fn.__name__
            self.listeners[name].append(fn)

        if func is None:
            return decorator
        else:
            decorator(func)

    def add_emitter(self, emitter: Emitter) -> None:
        emitter.pubs.append(self)

    async def wait_for(self, event_name: str, timeout: Optional[int]) -> Any:
        ...


