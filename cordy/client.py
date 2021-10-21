from __future__ import annotations

import asyncio
from logging import getLogger
from typing import TYPE_CHECKING, Any, Callable, Sequence, Type

import aiohttp

from .auth import Token
from .events import Emitter, Publisher
from .gateway import Sharder
from .http import HTTPSession
from .models import Intents

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from .auth import StrOrToken
    from .events import CheckFn, CoroFn
    from .gateway import BaseSharder, Shard

__all__ = (
    "Client",
)

logger = getLogger("cordy.client")

class Client:
    num_shards: int | None
    shard_ids: set[int] | None

    def __init__(
        self, token: StrOrToken, *,
        intents: Intents = None, sharder_cls: Type[BaseSharder[Shard]] = Sharder,
        num_shards: int = None, shard_ids: Sequence[int] = None
    ):
        self.intents = intents or Intents.default()
        self.token = token if isinstance(token, Token) else Token(token, bot=True)

        self.emitter = Emitter()
        self.publisher = Publisher(None)
        self.publisher.add(self.emitter)
        self.http = HTTPSession(aiohttp.ClientSession(), self.token)
        self.loop = asyncio.get_event_loop()

        if shard_ids is not None and num_shards is None:
            raise ValueError("Must provide num_shards if shard ids are provided.")

        if shard_ids is None and num_shards is not None:
            shard_ids = list (range(num_shards))

        self.shard_ids = set(shard_ids) if shard_ids else None
        self.num_shards = num_shards

        # May manipulate client attributes
        self.sharder = sharder_cls(self)

    @property
    def shards(self) -> list[Shard]:
        return self.sharder.shards

    def listen(self, name: str = None) -> Callable[[CoroFn], CoroFn]:
        def deco(func: CoroFn):
            self.publisher.subscribe(name or func.__name__.lower(), func)
            return func
        return deco

    def add_listener(self, func: CoroFn, name: str = None) -> None:
        return self.publisher.subscribe(name or func.__name__.lower(), func)

    def remove_listener(self, func: CoroFn, name: str = None) -> None:
        return self.publisher.unsubscribe(func, name)

    def wait_for(self, event_name: str, timeout: int = None, check: CheckFn = None) -> Coroutine[Any, Any, tuple[Any, ...]]:
        return self.publisher.wait_for(event_name, timeout, check)

    async def connect(self) -> None:
        await self.sharder.create_shards()
        await self.sharder.launch_shards()

    async def disconnect(self, *, code: int = 4000, message: str = "") -> None:
        for shard in self.shards:
            await shard.disconnect(code=code, message=message)

    async def reconnect(self) -> None:
         for shard in self.shards:
            await shard.reconnect()

