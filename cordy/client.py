from __future__ import annotations

import asyncio
from typing import Optional, TYPE_CHECKING

import aiohttp
from aiohttp import WSMsgType
from yarl import URL
import sys

from .http import Route

if TYPE_CHECKING:
    from aiohttp.client_ws import ClientWebSocketResponse

    from .models import Intents

__all__ = (
    'Client'
)


class Client:
    def __init__(self, intents: Optional[Intents]):
        self.intents = intents

    async def connect(self, token: str) -> None:
        headers: dict[str, str] = {}
        token = token.strip()

        headers["Authorization"] = "Bot " + token
        headers["User-Agent"] = "Cordy (https://github.com/BytesToBits/Cordy, 0.1.0)"

        endp = Route("GET", "/gateway")()
        url = URL((await (await aiohttp.request(endp.method, endp.url)).json())["url"])
        url %= {"v": 9, "encoding": "json"}

        s = None
        async def heartbeat(ws: ClientWebSocketResponse, interval: int):
            while not ws.closed:
                ws.send_json({"op": 1, "s": s})
                await asyncio.sleep(interval/1000)

        async with aiohttp.ClientSession() as ses:
            async with ses.ws_connect(url) as ws:
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        data = msg.json()
                        s = data.get("s", None)
                        if data["op"] == 10:
                            asyncio.create_task(heartbeat(ws, data["s"] - 100))
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
                        print(data)
                    elif msg.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING}:
                        await ws.close(code="1000")
                    elif msg.type == WSMsgType.ERROR:
                        raise Exception(msg)


    def disconnect(self) -> None:
        ...

    def reconnect(self) -> None:
        ...