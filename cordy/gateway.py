from __future__ import annotations

import asyncio
import logging
from time import perf_counter
import zlib
from enum import IntEnum
from sys import platform
from typing import TYPE_CHECKING, Any, ClassVar

from aiohttp import WSMsgType
from aiohttp.client_ws import ClientWebSocketResponse
from yarl import URL

from . import util

if TYPE_CHECKING:
    from .client import Client

logger = logging.getLogger(__name__)
# TODO: ETF, Pyrlang/Term, discord/erlpack

__all__ = (
    "GateWay",
)

Msg = dict[str, Any]

class LatencyTracker:
    def __init__(self) -> None:
        self._num_checks = 0
        self._last_latency = 0.0
        self.avg_latency = 0.0
        self._last_ten = []

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
            ret = cls._value2member_map_[val]
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

class GateWay:
    _PROPS: ClassVar[dict[str, str]] = {
        "$os": platform,
        "$browser": "cordy",
        "$device": "cordy"
    }

    ws: ClientWebSocketResponse

    def __init__(self, client: Client, *, inflator: Inflator = None) -> None:
        self.session = client.http
        self.token = client.token
        self.intents = client.intents
        self.inflator = inflator or Inflator()
        self.ws = None
        self.client = client

        self.loop = asyncio.get_event_loop()
        self._closed = False
        self._url = None

        self._seq = None
        self._session_id = ""
        self._interval = 0.0
        self._ack_fut = None
        self._tracker = LatencyTracker()
        self._beater = None

    async def connect(self, url: URL):
        url %= {"v": 9, "encoding": "json"}

        self.ws = await self.session.ws_connect(url)
        self._url = url

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
                    await self.ws.close()
                    logger.debug("Connection closed: %s", msg)
                    break

                self.loop.create_task(self.process_message(data))

            if self._reconnect:
                # TODO: RESUMING
                await self.connect(self._url)
                self._reconnect = False
            else:
                break

    async def process_message(self, msg: Msg) -> None:
        op = msg.get("op") # 0,1,7,9,10,11
        self._seq: int = msg.get("s") or self._seq

    async def close(self):
        self._closed = True
        await self.ws.close()

    async def hello(self, msg: Msg):
        self._interval: float = msg["d"]["heartbeat_interval"] / 1000

        self._beater = self.loop.create_task(self.heartbeat)
        await self.identify()

    async def heartbeat(self) -> None:
        while True:
            self._ack_fut = self.loop.create_future()
            await self.send({
                "op": OpCodes.HEARTBEAT.value,
                "d": self._seq
            })
            start = perf_counter()
            try:
                await asyncio.wait_for(self._ack_fut, timeout=self._interval)
            except asyncio.TimeoutError:
                self.ws.close(code=4000, message=b"zombied gateway connection")
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

    async def identify(self):
        data = {
            "op": 2,
            "d": {
                "token": self.token.get_auth(),
                "properties": self._PROPS,
                "intents": self.intents.value,
                "compress": True
            }
        }

        await self.send(data)

    async def resume(self):
        await self.send({
            "op": 6,
            "d": {
                "token": self.token.token,
                "session_id": self._session_id,
                "seq": self._seq
        }})

    async def send(self, data: Msg) -> None:
        # TODO: RateLimit, Coming Soon :tm:
        return await self.ws.send_str(util.dumps(data))

class Shard:
    connection: GateWay
    ...
