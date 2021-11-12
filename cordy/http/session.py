from __future__ import annotations

from typing import final, TYPE_CHECKING

from aiohttp import ClientSession

from .. import util
from .ratelimit import Delayer

if TYPE_CHECKING:
    from yarl import URL

    from ..auth import Token
    from ..util import Msg
    from .route import Endpoint, Route


@final
class HTTPSession:
    def __init__(self, token: Token) -> None:
        headers = {
            "Authorization": token.get_auth(),
            "User-Agent": "Cordy (https://github.com/BytesToBits/Cordy, 0.1.0)"
        }

        self.session = ClientSession(headers=headers)

    def ws_connect(self, url: URL, **kwargs):
        return self.session.ws_connect(url, **kwargs)

    async def request(self, endp: Endpoint | Route, **kwargs):
        if endp.url is None:
            raise ValueError(f"Used {type(endp)} instance with unformatted url")
        return await self.session.request(endp.method, endp.url, **kwargs)

    async def get_gateway(self) -> URL:
        async with self.request(Route("GET", "/gateway")) as res:
            return URL((await res.json(loads=util.loads))["url"])

    async def get_gateway_bot(self) -> Msg:
        async with self.request(Route("GET", "/gateway/bot")) as resp:
            ret: Msg = await resp.json(loads=util.loads)
            return ret

    async def close(self):
        return await self.session.close()
