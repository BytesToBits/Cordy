from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any, Callable
from logging import getLogger
import random

import aiohttp
from aiohttp import WSMsgType
from yarl import URL

from cordy.auth import StrOrToken, Token

from .events import CheckFn, CoroFn, Emitter, Publisher, Event
from .http import HTTPSession, Route
from .models import Intents

if TYPE_CHECKING:
    from aiohttp.client_ws import ClientWebSocketResponse
    from collections.abc import Coroutine

__all__ = (
    'Client',
)

logger = getLogger("cordy.client")

class Client:
    def __init__(self, token: StrOrToken, *, intents: Intents = None):
        if intents is None:
            self.intents = Intents.default()
        else:
            self.intents = intents

        self.emitter = Emitter()
        self.publisher = Publisher(None)
        self.publisher.add(self.emitter)
        self.loop = asyncio.get_event_loop()

        self.token = token if isinstance(token, Token) else Token(token, bot=True)
        self.http = HTTPSession(aiohttp.ClientSession())

    def listen(self, event_name: str = None) -> Callable[[CoroFn], CoroFn]:
        def deco(func: CoroFn):
            self.publisher.subscribe(event_name or func.__name__.lower(), func)
            return func
        return deco

    def add_listener(self, func: CoroFn, event_name: str = None) -> None:
        return self.publisher.subscribe(event_name or func.__name__.lower(), func)

    def remove_listener(self, func: CoroFn, event_name: str = None) -> None:
        return self.publisher.unsubscribe(func, event_name)

    def wait_for(self, event_name: str, timeout: int = None, check: CheckFn = None) -> Coroutine[Any, Any, tuple[Any, ...]]:
        return self.publisher.wait_for(event_name, timeout, check)

    async def connect(self) -> None:
        headers: dict[str, str] = {}

        headers["Authorization"] = self.token.get_auth()
        headers["User-Agent"] = "Cordy (https://github.com/BytesToBits/Cordy, 0.1.0)"

        async with aiohttp.ClientSession() as ses:

            endp = Route("GET", "/gateway").with_params()
            async with ses.request(endp.method, endp.url) as resp:
                url = URL((await resp.json(encoding="utf-8"))["url"])
                url %= {"v": 9, "encoding": "json"}

            s = None
            async def heartbeat(ws: ClientWebSocketResponse, interval: int):
                while not ws.closed:
                    logger.debug("----> %s", s)
                    await ws.send_json({"op": 1, "d": s}, dumps=lambda d: json.dumps(d, separators=(',', ':')))
                    logger.debug("Sent Heartbeat")
                    await asyncio.sleep(interval * random.random() / 1000)

            async with ses.ws_connect(url) as ws:
                while True:
                    msg = await ws.receive()
                    if not msg.data:
                        continue
                    logger.debug("Received Message")
                    logger.debug("Received msg: %s", msg.data)
                    if msg.type == WSMsgType.TEXT:
                        data = msg.json()
                        self.loop.create_task(self.emitter.emit(Event("on_socket_raw_receive", data)))

                        op = data["op"]
                        s = data.get("s", None) or s
                        if data["op"] == 10:
                            await ws.send_json({
                                "op": 2,
                                "d": {
                                    "token": self.token.token,
                                    "properties": {
                                        "$os": sys.platform,
                                        "$browser": "cordy",
                                        "$device": "cordy"
                                    },
                                    "intents": self.intents.value
                                }
                            })
                            asyncio.create_task(heartbeat(ws, data["d"]["heartbeat_interval"]))
                        elif op == 11:
                            logger.debug("Heartbeat ACK")
                    elif msg.type == WSMsgType.ERROR:
                        raise Exception(msg)
                    elif msg.type in {WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED}:
                        logger.debug("Closing Gateway Websocket")
                        await ws.close()
                        break

    def disconnect(self) -> None:
        ...

    def reconnect(self) -> None:
        ...
