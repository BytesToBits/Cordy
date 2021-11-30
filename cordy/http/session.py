from __future__ import annotations

from typing import final, TYPE_CHECKING

from aiohttp import ClientSession
from aiohttp.client import _RequestContextManager
from asyncio import Event
from yarl import URL

from .. import util
from .ratelimit import Delayer
from .route import Route

if TYPE_CHECKING:
    from yarl import URL
    from aiohttp.client_reqrep import ClientResponse

    from ..auth import Token
    from ..util import Msg
    from .route import Endpoint


@final
class HTTPSession:
    def __init__(self, token: Token) -> None:
        headers = {
            "Authorization": token.get_auth(),
            "User-Agent": "Cordy (https://github.com/BytesToBits/Cordy, 0.1.0)"
        }

        self.session = ClientSession(headers=headers)
        self.delayer = Delayer()
        self.global_limit = Event()
        self.global_limit.set()

        self._loop = self.session._loop

    def ws_connect(self, url: URL, **kwargs):
        return self.session.ws_connect(url, **kwargs)

    async def _request(self, endp: Endpoint | Route, **kwargs):
        if endp.url is None:
            raise ValueError(f"Used {type(endp)} instance with unformatted url")

        while True:
            await self.global_limit.wait()
            async with self.delayer.acquire(endp, timeout=kwargs.get("timeout")) as limit:
                resp = await self.session._request(endp.method, endp.url, **kwargs)
                hdrs = resp.headers

                if resp.status == 429:
                    is_global = hdrs.get("X-RateLimit-Global")
                    buc = hdrs.get("X-RateLimit-Bucket")
                    ts = hdrs.get("X-RateLimit-Reset")

                    if not is_global:
                        if ts:
                            limit.delay_till(float(ts), buc)
                    else:
                        self.global_limit
                        self._loop.call_at(ts or 1, self.global_limit.set)
                else:
                    return resp

    def request(self, endp: Endpoint | Route, **kwargs):
        return _RequestContextManager(self._request(endp, **kwargs))

    async def get_gateway(self) -> URL:
        async with self.request(Route("GET", "/gateway")) as res:
            return URL((await res.json(loads=util.loads))["url"])

    async def get_gateway_bot(self) -> Msg:
        async with self.request(Route("GET", "/gateway/bot")) as resp:
            ret: Msg = await resp.json(loads=util.loads)
            return ret

    async def send_message(self, channel_id: int | str, content: str): # basic prototype not for use
        async with self.request(Route("POST", "/channels/{channel_id}/messages") % dict(channel_id=channel_id), json=dict(content=content)) as res:
            return res

    async def close(self):
        return await self.session.close()
