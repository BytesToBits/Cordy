from __future__ import annotations

import asyncio
from logging import getLogger
from time import time
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable
from dataclasses import dataclass

from ..errors import RateLimitTooLong
from .route import Endpoint
from ..util import make_proxy_for

if TYPE_CHECKING:
    from .route import Route

logger = getLogger(__name__)

def _id_gen(initial: int):
    yield -1 # None receive

    while True:
        yield initial
        initial += 1

# Group of routes which share the same ratelimit
# per major parameters
@dataclass
class AbstractGroup:
    routes: set[Route]
    ident: int

    def __init__(self, ident: int) -> None:
        self.routes = set()
        self.ident = ident

    def add(self, route: Route):
        self.routes.add(route)

    def make_hash_for(self, endp: Endpoint) -> str:
        return hex(self.ident) + ":" + endp.param_hash

# A group of endpoints which share the same ratelimit
# bucket
@dataclass
class Group:
    abs_group: AbstractGroup
    hash: str

    __slots__ = ("abs_group", "hash")

    def __init__(self, abs_group: AbstractGroup, param_hash: str) -> None:
        self.abs_group = abs_group
        self.hash = hex(abs_group.ident) + ":" + param_hash

    # Secondary Functionality
    def __contains__(self, endp: Endpoint) -> bool:
        return (endp.param_hash == self.param_hash and
            endp.route in self.abs_group.routes)

    @property
    def param_hash(self) -> str:
        return self.hash.split(":")[1]

# Finds ratelimit groups independent of major parameters
# Used to share groups detected in one endpoint to other
# requiring same major parameters and methods.
# Allows for pre-emptive detection of ratelimit exhaustion
# on an endpoint
class Grouper:
    group_map: dict[Route, AbstractGroup]
    buckets: dict[str, Group]

    def __init__(self) -> None:
        self.group_map = {}
        self.buckets = {}
        self.__gen = _id_gen(1)
        self.__gen.send(None)

    def add(self, endp: Endpoint, bucket: str):
        a_group: AbstractGroup | None = getattr(self.buckets.get(bucket), "abs_group", None)
        route = endp.route

        if a_group:
            if route not in a_group.routes:
                a_group.add(route)
                self.group_map[route] = a_group
        else:
            a_group = self.group_map.get(route)

            if a_group:
                self.buckets[bucket] = Group(a_group, endp.param_hash)
            else:
                a_group = AbstractGroup(self.__gen.send(None))
                self.buckets[bucket] = Group(a_group, endp.param_hash)

            a_group.add(route)
            self.group_map[route] = a_group

    def get_group(self, endp: Endpoint) -> Group:
        a_group = self.group_map[endp.route]

        return Group(a_group, endp.param_hash)

@runtime_checkable
class BaseLimiter(Protocol):
    limited: asyncio.Event
    resets_at: float

    async def __aenter__(self) -> BaseLimiter:
        ...

    async def __aexit__(self, *_) -> bool:
        ...

    def delay_till(self, timestamp: float, bucket: str | None) -> None:
        ...

class Limiter:
    __slots__ = ("limited","resets_at")

    def __init__(self) -> None:
        self.limited = asyncio.Event()
        self.limited.set()
        self.resets_at = 0.0

    async def __aenter__(self) -> Limiter:
        await self.limited.wait()
        return self

    async def __aexit__(self, *_) -> Literal[False]:
        return False

    def delay_till(self, timestamp: float, bucket: str | None) -> None:
        loop = asyncio.get_running_loop()
        delta = (timestamp - time())
        self.resets_at = timestamp
        if delta > 0:
            self.limited.clear()
            loop.call_at(loop.time() + delta, self.limited.set)

class LazyLimiter(Limiter):
    __slots__ = ("endp", "delayer")
    endp: Endpoint
    delayer: Delayer

    def __init__(self, delayer: Delayer, endp: Endpoint) -> None:
        self.delayer = delayer
        self.endp = endp
        super().__init__()

    def delay_till(self, timestamp: float, bucket: str | None) -> None:
        if not bucket:
            return

        delayer = self.delayer
        grouper = delayer.grouper
        grouper.add(self.endp, bucket)
        abs_group = grouper.group_map[self.endp.route]
        param_hash = abs_group.make_hash_for(self.endp)

        bucket_limiter = delayer.grouped_buckets.get(param_hash)

        if not bucket_limiter:
            bucket_limiter = delayer.grouped_buckets[param_hash] = Limiter()
            bucket_limiter.delay_till(timestamp, bucket)

        self.limited = bucket_limiter.limited

# This is a proxy since max_wait changes between calls
@make_proxy_for(Limiter, attr="_limiter", proxied_methods=("delay_till",))
class TimedLimiterProxy:
    _limiter: Limiter

    def __init__(self, limiter: Limiter, *, max_wait: float):
        self._limiter = limiter
        self.max_wait = max_wait

    async def __aenter__(self):
        delta = time() - self._limiter.resets_at
        # Pre-emptive for minimal error response latency.
        if delta > self.max_wait:
            raise RateLimitTooLong("Sleep needed exceeded timeout")
        else:
            # There is no way the timestamp and event mismatch.
            # We may simply ignore the possibility of sleeping more
            # since that should be handled by higher level api.
            return await self._limiter.__aenter__()

    async def __aexit__(self, *exc_info):
        return self._limiter.__aexit__(*exc_info)

if TYPE_CHECKING:
    from typing import cast
    TimedLimiterProxy = cast(type[BaseLimiter], TimedLimiterProxy) # type: ignore[pyright]

class Delayer:
    grouper: Grouper
    grouped_buckets: dict[str, Limiter]

    def __init__(self) -> None:
        self.grouped_buckets = {}
        self.grouper = Grouper()

    def acquire(self, endp: Endpoint, timeout: float = None) -> BaseLimiter:
        a_group = self.grouper.group_map.get(endp.route)

        if a_group:
            param_hash = a_group.make_hash_for(endp)
            limiter = self.grouped_buckets.get(param_hash)
            if not limiter:
                self.grouped_buckets[param_hash] = limiter = Limiter()
        else:
            limiter = LazyLimiter(self, endp)

        if timeout is not None and isinstance(timeout, float):
            return TimedLimiterProxy(limiter, max_wait=timeout) # type: ignore[pyright]

        return limiter
