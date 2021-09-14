from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING, Optional
from logging import getLogger
import random

import aiohttp
from aiohttp import WSMsgType
from yarl import URL

from .http import Route
from .models import Intents

if TYPE_CHECKING:
    from aiohttp.client_ws import ClientWebSocketResponse

__all__ = (
    'Client'
)

logger = getLogger("cordy.client")

class Client:
    def __init__(self, intents: Optional[Intents] = None):
        if intents is None:
            self.intents = Intents.default()
        else:
            self.intents = intents

    async def connect(self, token: str) -> None:
        headers: dict[str, str] = {}
        token = token.strip()

        headers["Authorization"] = "Bot " + token
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
                        op = data["op"]
                        s = data.get("s", None) or s
                        if data["op"] == 10:
                            await ws.send_json({
                                "op": 2,
                                "d": {
                                    "token": token,
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
