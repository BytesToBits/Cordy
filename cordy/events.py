from __future__ import annotations

import asyncio
import types
from collections.abc import Coroutine, Generator
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Callable, Protocol, TypeVar, cast, overload

if TYPE_CHECKING:
    EV = TypeVar("EV", contravariant=True)

    class Observer(Protocol[EV]):
        def __call__(self, event: EV) -> None:
            ...

__all__ = (
    "Emitter",
    "Event",
    "Filter",
    "Publisher"
)

# Event System Design:
#  Emitter/Filter -> Publisher._notifier.send(event) -> Publisher._notifier -> Task<Publisher._notify(event)>
#                 ->   _Filter_relayer.send(event)   ->   _Filter_relayer   -> Filter.emit(event)

# TODO: Make integrations with reactive data streams.
#   basically make the Emmiter work in place of Observable
#   so that reactive paradigm can be used as an alternative

CoroFn = Callable[..., Coroutine]
CheckFn = Callable[..., bool]

_aliases = types.MappingProxyType({
    "message": "message_create",
    "member_join": "guild_member_add",
    "member_leave": "guild_member_remove",
    "member_update": "guid_member_update",
    "role_create": "guild_role_create",
    "role_update": "guild_role_update",
    "role_delete": "guild_role_delete",
    "message_purge": "message_delete_bulk",
    "typing": "typing_start"
})

def _clean_event(name: str):
    ret = name.casefold().removeprefix("on_")

    return _aliases.get(ret, ret)

class Event:
    __slots__ = ("name", "args")

    name: str
    args: tuple

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
    if TYPE_CHECKING:
        _obvrs: set[Observer[Event]]

    def __init__(self) -> None:
        self._obvrs = set()

    def emit(self, event: Event) -> None:
        to_remove = []
        for obs in self._obvrs:
            try:
                if obs(event) is not None:
                    to_remove.append(obs)
            except StopIteration:
                # Observor maybe a generator's method
                # which would make sense since they
                # are more effiecient at receiving and
                # sending values
                to_remove.append(obs)

        for closed in to_remove:
            self._obvrs.discard(closed)

    def filter(self, func: FilterFn):
        return Filter(func, self)

    def _add_observer(self, obs):
        self._obvrs.add(obs)

    def _discard_observer(self, obs):
        self._obvrs.discard(obs)

class Filter(Emitter):
    def __init__(self, filter_fn: FilterFn, source: Emitter) -> None:
        super().__init__()
        self.filter_fn = filter_fn
        gen = _Filter_relayer(self)
        gen.send(None)
        source._add_observer(gen.send)
        self.__gen = gen

    def emit(self, event: Event) -> None:
        if self.filter_fn(event):
            return super().emit(event)

    def __del__(self):
        try:
            self.__gen.close()
        except AttributeError:
            pass

def _Filter_relayer(self: Filter):
    ev = yield

    while True:
        ev = yield
        self.emit(ev)

class Publisher:
    waiters: dict[str, set[tuple[asyncio.Future[tuple], CheckFn | None]]]
    listeners: dict[str, set[CoroFn]]
    emitters: dict[Emitter, Generator[None, Event, None]]

    def __init__(self, error_hdlr: Callable[[Exception], Coroutine] = None) -> None:
        self.waiters = dict()
        self.listeners = dict()
        self.emitters = dict()
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

    def _notifier(self):
        event = yield

        while True:
            event = yield
            asyncio.create_task(self._notify(event))

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
        def decorator(fn: CoroFn) -> CoroFn:
            if not iscoroutinefunction(fn):
                raise TypeError(f"Expected a coroutine function got {type(fn)}.")
            nonlocal name
            name = _clean_event(name or fn.__name__)
            listeners = self.listeners.get(name, None) # type: ignore[arg-type]
            if listeners is None:
                self.listeners[name] = listeners = set() # type: ignore[index]
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

    async def wait_for(self, name: str, timeout: int = None, check: CheckFn = None) -> tuple:
        name = _clean_event(name)
        ev_waiters = self.waiters.get(name)
        if ev_waiters is None:
            self.waiters[name] = ev_waiters = set()

        fut: asyncio.Future[tuple] = asyncio.get_running_loop().create_future()
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
        gen = self.emitters.get(emitter, None)
        if gen is not None:
            gen.close()
            emitter._discard_observer(gen.send)

        self.emitters[emitter] = notif = self._notifier()
        notif.send(None)
        emitter._add_observer(notif.send)

    def remove(self, emitter: Emitter) -> None:
        gen = self.emitters.get(emitter, None)
        if gen is None:
            return
        else:
            gen.close()
            emitter._discard_observer(gen.send)
            del self.emitters[emitter]

# Pros - less overhead for listeners
#   subscribing for particular event
# Cons - Narrow use case, overhead reduction is low.
class SourcedPublisher(Publisher, Emitter):
    def __init__(self, error_hdlr: Callable[[Exception], Coroutine] = None) -> None:
        super().__init__(error_hdlr=error_hdlr)
        Emitter.__init__(self)

    def filter(self, func: FilterFn) -> FilteredPublisher:
        return FilteredPublisher(func, self, self.err_hdlr)

    def emit(self, event: Event) -> None:
        super().emit(event)
        asyncio.create_task(self._notify(event))

class FilteredPublisher(SourcedPublisher, Filter):
    def __init__(self, filter_fn: FilterFn, source: Emitter, error_hdlr: Callable[[Exception], Coroutine] = None) -> None:
        super().__init__(error_hdlr=error_hdlr)
        Filter.__init__(self, filter_fn, source)

    def emit(self, event: Event) -> None:
        if self.filter_fn(event):
            super(Filter, self).emit(event)
            asyncio.create_task(self._notify(event))
