from __future__ import annotations

import asyncio
import logging
import zlib
from enum import IntEnum
from json import load
from sys import platform
from time import perf_counter
from typing import (TYPE_CHECKING, Any, ClassVar, Protocol, Sequence, TypeVar,
                    runtime_checkable)

import aiohttp
from aiohttp import WSMsgType
from aiohttp.client_ws import ClientWebSocketResponse
from yarl import URL

from . import util
from .http import Route

if TYPE_CHECKING:
    from .client import Client
    from .events import Emitter
    from .util import Msg

logger = logging.getLogger(__name__)
# TODO: ETF, Pyrlang/Term, discord/erlpack

__all__ = (
    "GateWay",
)



class LatencyTracker:
    def __init__(self) -> None:
        self._num_checks = 0
        self._last_latency = 0.0
        self.avg_latency = 0.0
        self._last_ten: list[float] = []

    @property
    def latency(self) -> float:
        return self._last_latency

    @latency.setter
    def latency(self, val: float) -> None:
        self._last_ten.append(self._last_latency)
        if len(self._last_ten) > 10:
            self._last_ten.pop(0)

        self._last_latency = val

        self.avg_latency = ((self._num_checks * self.avg_latency) + val) / (self._num_checks + 1)
        self._num_checks += 1

    @property
    def last_ten(self) -> tuple[float, ...]:
        return tuple(self._last_ten)

    reset = __init__

class OpCodes(IntEnum):
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE = 3
    VOICE_STATE = 4
    VOICE_PING = 5 # Only used by clients, does not need to be used.
    RESUME = 6
    RECONNECT = 7
    REQUEST_MEMBERS = 8
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11

    @classmethod
    def get_enum(cls, val: int) -> OpCodes | None:
        try:
            ret: OpCodes = cls._value2member_map_[val] # type: ignore[index]
        except KeyError:
            logger.info("Invalid OpCodes enum requested: %s", val)
            return None
        else:
            return ret


class Inflator: # for zlib
    """A Callable which decompresses incoming zlib data.

    Attributes
    ----------
    buf : :class:`bytearray`
        The data buffer.
    decomp : :class:`zlib.Decompress`
        The zlib context used for decompressing.
    """
    def __init__(self, **opt):
        self.buf = bytearray()
        self.decomp = zlib.decompressobj(**opt)

    def __call__(self, data: bytes) -> str | None:
        self.buf.extend(data)

        if len(data) >= 4 and data[-4:] == b'\x00\x00\xff\xff':
            msg = self.decomp.decompress(data).decode("utf=8")
            self.buf.clear()
            return msg

        return None

class GateWay:
    _PROPS: ClassVar[dict[str, str]] = {
        "$os": platform,
        "$browser": "cordy",
        "$device": "cordy"
    }

    ws: ClientWebSocketResponse | None

    def __init__(self, client: Client, *, inflator: Inflator = None, shard_id: int = 0) -> None:
        self.session = client.http
        self.token = client.token
        self.intents = client.intents
        self.inflator = inflator or Inflator()
        self.ws = None
        self.client = client
        self.shard_id = shard_id

        self.loop = asyncio.get_event_loop()
        self._closed = False
        self._url = None

        self._seq = None
        self._session_id = ""
        self._interval = 0.0
        self._ack_fut = None
        self._tracker = LatencyTracker()
        self._beater = None
        self._resume = True
        self._listener = None

    @property
    def resumable(self) -> bool:
        return self._resume and bool(self._session_id)

    async def connect(self, url: URL = None) -> None:
        if self._closed:
            raise ValueError("GateWay instance already closed")

        if self.ws and not self.ws.closed:
            self.disconnect(b"Reconnecting")

        url = url or self._url or await self._get_gateway()
        url %= {"v": 9, "encoding": "json"}

        try:
            self.ws = await self.session.ws_connect(url)
        except aiohttp.ServerTimeoutError:
            logger.warning("Shard %s | Gateway websocket connection timed-out", self.shard_id)
            raise
        except aiohttp.WSServerHandshakeError:
            logger.warning("Shard %s | Gateway websocket handshake failed.", self.shard_id)
            raise

        self._url = url

        if self._listener and self._listener.done():
            self._listener._log_traceback = False
        else:
            self._listener.cancel()

            self._listener = self.loop.create_task(self.listen())

        if self.resumable:
            await self.resume()
        else:
            await self.identify()

    async def listen(self):
        while not self._closed:
            while not self.ws.closed:
                msg = await self.ws.receive()

                if msg.type == WSMsgType.TEXT:
                    data = msg.json(loads=util.loads)
                elif msg.type == WSMsgType.BINARY:
                    data = self.inflator(msg.data)
                    if data:
                        data = util.loads(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    raise Exception(msg)
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                    logger.debug("Connection closed: %s", msg)
                    break

                self.loop.create_task(self.process_message(data))

            if self._reconnect:
                await self.connect(self._url)
                self._reconnect = False
            else:
                break

    async def process_message(self, msg: Msg) -> None:
        op = OpCodes.get_enum(msg.get("op")) # 0,1,7,9,10,11
        self._seq: int = msg.get("s") or self._seq

        if op is None:
            logger.warning("Gateway sent payload with unknown op code %s", msg.get("op"))
            return

        await getattr(self, op.name.lower())(msg)

    async def close(self):
        self._closed = True
        await self.disconnect(code=1001)

    async def hello(self, msg: Msg):
        self._interval: float = msg["d"]["heartbeat_interval"] / 1000

        if self._beater is not None:
            if self._beater.done():
                self._beater._log_traceback = False
            else:
                self._beater.cancel()

        self._beater = self.loop.create_task(self.heartbeater)

    async def heartbeat(self, _: Msg):
        self.send({
            "op": OpCodes.HEARTBEAT.value,
            "d": self._seq
        })

    async def heartbeater(self) -> None:
        while not self.ws.closed:
            self._ack_fut = self.loop.create_future()
            await self.send({
                "op": OpCodes.HEARTBEAT.value,
                "d": self._seq
            })
            start = perf_counter()
            try:
                await asyncio.wait_for(self._ack_fut, timeout=self._interval)
            except asyncio.TimeoutError:
                self.disconnect(message=b"zombied gateway connection")
                self._reconnect = True
                break
            else:
                self._tracker.latency = ack_latency = perf_counter() - start
                # 100 ms tolerance for system+connection latency
                await asyncio.sleep(self._interval - ack_latency - 0.1)

    async def heartbeat_ack(self, _: Msg) -> None:
        if self._ack_fut is None: # this should not happen
            fut = self.loop.create_future()
            self._ack_fut = fut

        if not self._ack_fut.done():
            self._ack_fut.set_result(True)
        else:
            # second acknowledge on same future
            # API fault? timing fault? Lib fault?
            # either way ignore this
            pass

    async def identify(self) -> None:
        data = {
            "op": 2,
            "d": {
                "token": self.token.get_auth(),
                "properties": self._PROPS,
                "intents": self.intents.value,
                "compress": True,
                "shard": (self.shard_id, self.client.num_shards)
            }
        }

        await self.send(data)

    async def resume(self) -> None:
        await self.send({
            "op": 6,
            "d": {
                "token": self.token.token,
                "session_id": self._session_id,
                "seq": self._seq
        }})

    async def invalid_session(self, msg: Msg) -> None:
        self._resume = msg["d"]
        self._reconnect = False # exit listener

        self._seq = None
        self._session_id = ""

        await self.disconnect(code=4000 if self._resume else 1000)
        await asyncio.sleep(1.0) # sleep for  1-5 seconds

        if not self._listener or self._listener.done():
            await self.connect(self._url)

    async def reconnect(self, _: Msg) -> None:
        self._reconnect = True
        self._resume = True

        await self.disconnect(message=b"Reconnect request")

        if not self._listener or self._listener.done():
            await self.connect(self._url)

    async def dispatch(self, msg: Msg) -> None:
        event: str = msg.get("t")
        data: Msg = msg.get("d")

        if event == "READY":
            self._session_id: str = data.get("session_id")
            self._resume = True

    async def disconnect(self, code: int = 4000, message: bytes = b"") -> None:
        await self.ws.close(code=code, message=message)
        self._tracker.reset()

    async def send(self, data: Msg) -> None:
        # TODO: RateLimit, Coming Soon :tm:
        return await self.ws.send_str(util.dumps(data))

class Shard:
    gateway: GateWay
    emitter: Emitter
    id: int

    def __init__(self, client: Client, id_: int = 0) -> None:
        self.id = id_
        self.client = client
        self.gateway = GateWay(client, shard_id=id_)

    def launch(self, url: URL | None) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as err:
            import os
            from threading import get_ident
            raise Exception(f"Thread {get_ident()}, PID {os.getpid()}. No running event loop!") from err

        loop.create_task(self.gateway.connect(url))

S = TypeVar("S")

@runtime_checkable
class BaseSharder(Protocol[S]):
    client: Client
    _url: URL | None

    def __init__(self, client: Client) -> None:
        self.client = client
        self._url = None

    @property
    def num_shards(self):
        return self.client.num_shards

    @property
    def shard_ids(self):
        return self.client.shard_ids

    async def create_shards(self) -> Sequence[S]:
        ...

    async def launch_shards(self, shards: Sequence[S]) -> None:
        ...

    def shard() -> None:
        ...


class Sharder(BaseSharder[Shard]):
    async def create_shards(self) -> list[Shard]:
        if self.num_shards is None:
            # don't cache the session limit
            # coz delay till launch is unknown
            data = await self.client.http.get_gateway_bot()
            self._url = URL(data["url"])
            self.client.num_shards = data["shards"]
            self.client.shard_ids = self.shard_ids or set(range(data["shards"]))

        shards = []

        for id_ in self.shard_ids:
            shards.append(Shard(self.client, id_))

        return shards

    async def launch_shards(self, shards: Sequence[Shard]) -> None:
        url = self._url

        for shard in shards:
            shard.launch(url)

    async def shard(self):
        return await self.launch_shards(await self.create_shards(self.client))
