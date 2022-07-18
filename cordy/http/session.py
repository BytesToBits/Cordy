from __future__ import annotations

from typing import final, TYPE_CHECKING
from time import time

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

                buc = hdrs.get("X-RateLimit-Bucket")
                rem = hdrs.get("X-RateLimit-Remaining")

                if resp.status == 429 or int(rem or -1) == 0:
                    is_global = hdrs.get("X-RateLimit-Global")
                    ts = hdrs.get("X-RateLimit-Reset")

                    if not is_global:
                        if ts:
                            limit.delay_till(float(ts), buc)
                    else:
                        self.global_limit.clear()
                        now = time()
                        self._loop.call_later(float(ts or now) - now, self.global_limit.set)
                else:
                    # discover route <-> bucket relation
                    if buc:
                        self.delayer.grouper.add(endp, buc)
                    return resp
            timeout -= timer.stop() # type: ignore # guaranteed to be float, nocast

    # return annotation fixes mypy
    def request(self, endp: Endpoint, **kwargs) -> _RequestContextManager:
        return _RequestContextManager(self._request(endp, **kwargs))

    # why does pyright say the return type is Ret | None for these 3?
    # might disable pyright type checking in next related commit and turn on warn unused ignore in mypy
    async def get_gateway(self) -> URL: # type: ignore[pyright]
        async with self.request(GATEWAY) as res:
            return URL((await res.json(loads=util.loads))["url"])

    async def get_gateway_bot(self) -> Msg: # type: ignore[pyright]
        async with self.request(GATEWAY_BOT) as resp:
            ret: Msg = await resp.json(loads=util.loads)
            return ret

    # NOTFORUSE
    async def send_message(self, channel_id: int | str, content: str) -> ClientResponse: # type: ignore[pyright]
        async with self.request(POST_MSG % dict(channel_id=channel_id), json=dict(content=content)) as res:
            return res

    async def close(self):
        return await self.session.close()
