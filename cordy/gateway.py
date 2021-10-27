from __future__ import annotations

import asyncio
import logging
import zlib
from enum import IntEnum
from math import log10 as _log
from sys import platform
from time import perf_counter
from typing import (TYPE_CHECKING, ClassVar, Protocol, TypeVar,
                    runtime_checkable)

import aiohttp
from aiohttp import WSMsgType
from aiohttp.client_ws import ClientWebSocketResponse
from yarl import URL

from cordy.events import Event, SourcedPublisher

from . import util

if TYPE_CHECKING:
    from asyncio.futures import Future
    from asyncio.locks import Lock
    from asyncio.tasks import Task

    from .client import Client
    from .types import Dispatch, Payload
    from .util import Msg

logger = logging.getLogger(__name__)
# TODO: ETF, Pyrlang/Term, discord/erlpack

__all__ = (
    "GateWay",
    "BaseSharder",
    "Sharder",
    "SingleSharder"
)

class LatencyTracker:
    """The connection latency tracker.
    This keeps a track of the latency of a connection.
    The type of latency which is tracked depends on the class
    the tracker is bound to.
    For example, a tracker boud to :class:`.Gateway`
    tracks the heartbeat latency.

    Attributes
    ----------
    avg_latency : :class:`float`
        The average latency, this is the average of all recorded latencies.
    """
    def __init__(self) -> None:
        self._num_checks = 0
        self._last_latency = 0.0
        self.avg_latency = 0.0
        self._last_ten: list[float] = []

    @property
    def latency(self) -> float:
        """:class:`float` : The last recorded latency"""
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
        """tuple[:class:`float`, ...], (:class:`tuple`) : A tuple with last 10 recorded latencies"""
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
    stream : :class:`bool`
        Whether the the data is a part of zlib-stream
    """
    def __init__(self, stream: bool = False, **opt):
        self.buf = bytearray()
        self.stream = stream
        self.decomp = zlib.decompressobj(**opt)

    def __call__(self, data: bytes) -> str | None:
        if not self.stream:
            try:
                return zlib.decompress(data).decode("utf-8")
            except zlib.error:
                self.buf.extend(data)

        if len(data) < 4 or data[-4:] != b'\x00\x00\xff\xff':
            return None

        msg = self.decomp.decompress(self.buf).decode("utf-8")
        self.buf = bytearray()
        return msg

# TODO: Consider Async initialisation to remove checks
class GateWay:
    """The Gateway connection manager.
    This is a low level construct which should not be interacted with
    directly.
    """
    _PROPS: ClassVar[dict[str, str]] = {
        "$os": platform,
        "$browser": "cordy",
        "$device": "cordy"
    }

    ws: ClientWebSocketResponse | None
    _url: URL | None
    _listener: Task[None] | None
    _beater: Task[None] | None
    _reconnect: bool
    _seq: int | None
    _interval: float | None
    _ack_fut: Future | None

    def __init__(self, client: Client, *, shard: Shard, inflator: Inflator = None, compression: bool = False) -> None:
        self.session = client.http
        self.token = client.token
        self.intents = client.intents
        self.inflator = inflator or Inflator()
        self.inflator.stream = compression
        self.ws = None
        self.client = client
        self.shard_id = shard.shard_id
        self.emitter = shard.emitter
        self.shard = shard

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
        self._reconnect = True
        self._reconnecting = False
        self._compression = compression

    @property
    def resumable(self) -> bool:
        return self._resume and bool(self._session_id)

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def disconnected(self) -> bool:
        return self.ws is not None and self.ws.closed

    @property
    def connected(self) -> bool:
        return not self.disconnected

    async def connect(self, url: URL = None) -> None:
        if self._closed:
            raise ValueError("GateWay instance already closed")

        if self.ws and not self.ws.closed:
            await self.disconnect(message=b"Reconnecting")

        url = url or self._url or await self.session.get_gateway()
        url %= {"v": 9, "encoding": "json"}

        if self._compression:
            url %= {"compress": "zlib-stream"}

        try:
            self.ws = await self.session.ws_connect(url)
        except aiohttp.ServerTimeoutError:
            logger.warning("Shard %s | Gateway websocket server timed-out", self.shard_id)
            return
        except aiohttp.WSServerHandshakeError:
            logger.warning("Shard %s | Gateway websocket handshake failed.", self.shard_id)
            return
        except aiohttp.ClientConnectionError as err:
            logger.warning("Shard %s | Can't connect to server: %s", self.shard_id, err)
            return

        logger.info("Shard %s connected to gateway", self.shard_id)

        self._url = url
        self._reconnect = True

        self._listener is not None and self._listener.cancel()

        self._listener = self.loop.create_task(self.listen())

    async def listen(self):
        if self.ws is None:
            return

        backoff = 1
        reconnecting = False
        zombie_listener = False

        while not self._closed:
            if reconnecting:
                delay = 2 * backoff * _log(backoff)
                logger.info("Disconnected, reconnecting again in %s", delay)
                await asyncio.sleep(delay)
                backoff = (backoff + 1) % 700 # limit sleep to around 2000 sec

            if zombie_listener and not reconnecting:
                break

            while not self.ws.closed:
                data: Payload | None = None
                msg = await self.ws.receive()

                if msg.type == WSMsgType.TEXT:
                    data = msg.json(loads=util.loads)
                elif msg.type == WSMsgType.BINARY:
                    if (_json := self.inflator(msg.data)):
                        data = util.loads(_json)
                elif msg.type == WSMsgType.ERROR:
                    raise Exception(msg)
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                    logger.debug("Connection closed: %s", msg)
                    break
                else:
                    continue # ensure data is bound

                if data is not None:
                    self.loop.create_task(self.process_message(data))

            if self._reconnect:
                await self.connect(self._url)
                reconnecting = self.disconnected
                zombie_listener = True
            else:
                break


    async def process_message(self, msg: Payload) -> None:
        op = OpCodes.get_enum(msg["op"]) # 0,1,7,9,10,11
        self._seq = msg.get("s") or self._seq

        if op is None:
            logger.warning("Gateway sent payload with unknown op code %s", msg.get("op"))
            return

        logger.debug("Shard %s Received: %s", self.shard_id, msg)

        await getattr(self, op.name.lower())(msg)

    async def start_session(self):
        if self.resumable:
            await self.resume()
        else:
            await self.identify()

    async def close(self):
        self._closed = True
        await self.disconnect(code=1001)

    async def hello(self, msg: Msg):
        self._interval = msg["d"]["heartbeat_interval"] / 1000

        if self._beater is not None:
            self._beater.cancel()

        self._beater = self.loop.create_task(self.heartbeater())
        self.loop.create_task(self.start_session())

    async def heartbeat(self, _: Msg):
        self.send({
            "op": OpCodes.HEARTBEAT.value,
            "d": self._seq
        })

    async def heartbeater(self) -> None:
        if self.ws is None or self._interval is None:
            return

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
                await self.disconnect(message=b"zombied gateway connection")
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
                "token": self.token.token,
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

    async def reconnect(self, _: Payload = None) -> None:
        logger.debug("Shard %s Reconnecting...")
        self._reconnect = True
        self._resume = True

        await self.disconnect(message=b"Reconnect request")

        if not self._listener or self._listener.done():
            await self.connect(self._url)

    async def dispatch(self, msg: Dispatch) -> None:
        event: str = msg["t"]
        data = msg["d"]

        if not data:
            return

        if event == "READY":
            self._session_id = data["session_id"]
            self._resume = True

        self.emitter.emit(Event(event, data, self.shard))

    async def disconnect(self, *, code: int = 4000, message: bytes = b"") -> None:
        if not self.ws:
            return

        await self.ws.close(code=code, message=message)
        self._tracker.reset()
        self._beater and self._beater.cancel()

        self.emitter.emit(Event("disconnect", self.shard))

    async def send(self, data: Msg) -> None:
        # TODO: RateLimit, Coming Soon :tm:
        if self.ws:
            logger.debug("Shard %s Sending: %s", self.shard_id, data)
            await self.ws.send_str(util.dumps(data))

class Shard:
    gateway: GateWay
    emitter: SourcedPublisher
    shard_id: int

    def __init__(self, client: Client, shard_id: int = 0) -> None:
        self.shard_id = shard_id
        self.client = client
        self.emitter = SourcedPublisher()
        client.publisher.add(self.emitter)
        self.gateway = GateWay(client, shard=self)

    async def connect(self):
        if self.gateway.closed:
            self.gateway = GateWay(self.client, shard=self)

        await self.gateway.connect()

    async def close(self):
        await self.gateway.close()

    async def disconnect(self, *, code: int = 4000, message: str = "") -> None:
        return await self.gateway.disconnect(code=code, message=message.encode("utf-8"))

    async def reconnect(self):
        # it properly reconnects and resumes
        # this is an alias
        await self.connect()

    @property
    def latency(self) -> float:
        return self.gateway._tracker.latency

S = TypeVar("S")

@runtime_checkable
class BaseSharder(Protocol[S]):
    client: Client
    _url: URL | None
    shards: list[S]

    def __init__(self, client: Client) -> None:
        self.client = client
        self._url: URL | None = None
        self.shards: list[S] = []

    @property
    def num_shards(self):
        return self.client.num_shards

    @property
    def shard_ids(self):
        return self.client.shard_ids

    async def create_shards(self) -> None:
        ...

    async def launch_shards(self) -> None:
        ...

    def shard(self) -> None:
        ...


class Sharder(BaseSharder[Shard]):
    def __init__(self, client: Client) -> None:
        self.client = client
        self._url = None
        self.shards = []

    async def create_shards(self):
        if not self.num_shards:
            # don't cache the session limit
            # coz delay till launch is unknown
            data = await self.client.http.get_gateway_bot()
            self.client.num_shards = data["shards"]
            self.client.shard_ids = self.shard_ids or set(range(data["shards"]))

        shards = []

        for id_ in self.shard_ids:
            shards.append(Shard(self.client, id_))

        self.shards = shards

    async def launch_shards(self) -> None:
        if not self.shards:
            await self.create_shards()
        url = self._url
        loop = asyncio.get_event_loop()

        # session object can't be cached
        data = await self.client.http.get_gateway_bot()
        limit = data["session_start_limit"]

        max_conc: int = limit["max_concurrency"]

        buckets = [asyncio.Lock() for _ in range(max_conc)]

        async def runner(sd: Shard, lock: Lock):
            async with lock:
                await sd.gateway.connect(url)

        await asyncio.wait([loop.create_task(runner(sd, buckets[sd.shard_id % max_conc])) for sd in self.shards])

class SingleSharder(BaseSharder[Shard]):
    async def create_shards(self) -> None:
        self.shards = [Shard(self.client, 0)]

        self.client.num_shards = 1
        self.client.shard_ids = {0,} #

    async def launch_shards(self) -> None:
        if not self.shards:
            await self.create_shards()

        sd = self.shards[0]

        await sd.connect()

