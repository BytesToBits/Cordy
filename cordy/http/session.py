from __future__ import annotations

from typing import final, TYPE_CHECKING, overload

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

GATEWAY = Route("GET", "/gateway").with_params()
GATEWAY_BOT = Route("GET", "/gateway/bot").with_params()
POST_MSG = Route("POST", "/channels/{channel_id}/messages")

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

    async def _request(self, endp: Endpoint, *, timeout: float = -1, **kwargs):
        if endp.url is None:
            raise ValueError(f"Used {type(endp)} instance with unformatted url")

        timer = util.Timer()
        # We use a timer to pre-emptively avoid waits if they go beyond timeout
        # The logic is, failing early allows for a more responsive bot incase the request is ratelimited
        # due to any reason, with asyncio.wait_for we would wait for the entire period till timeout
        while True:
            timer.start()
            await self.global_limit.wait()
            async with self.delayer.acquire(endp, timeout=timeout) as limit:
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
                        self._loop.call_at(float(ts or 1), self.global_limit.set)
                else:
                    return resp
            timer.stop()
            timeout -= timer.time # type: ignore # guaranteed to be float, nocast

    def request(self, endp: Endpoint, **kwargs):
        return _RequestContextManager(self._request(endp, **kwargs))

    async def get_gateway(self) -> URL:
        async with self.request(GATEWAY) as res:
            return URL((await res.json(loads=util.loads))["url"])

    async def get_gateway_bot(self) -> Msg:
        async with self.request(GATEWAY_BOT) as resp:
            ret: Msg = await resp.json(loads=util.loads)
            return ret

    async def send_message(self, channel_id: int | str, content: str): # basic prototype not for use
        async with self.request(POST_MSG % dict(channel_id=channel_id), json=dict(content=content)) as res:
            return res

    async def close(self):
        return await self.session.close()
