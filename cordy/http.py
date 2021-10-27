from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal

from aiohttp import ClientSession
from yarl import URL

from . import util

if TYPE_CHECKING:
    from .auth import Token
    from .util import Msg

__all__ = (
    "Route",
    "Endpoint",
)

# TODO: Make buckets for ratelimits
# MAYBE: Remove cache if global instances are used
Methods = Literal["GET", "PUT", "PATCH", "POST", "DELETE"]

class Endpoint:
    __slots__ = ("route", "url")

    route: Route
    url: URL

    def __init__(self, route: Route, params: dict[str, str]) -> None:
        self.route = route
        self.url = self.route.BASE / route.path.format_map(params)

    @property
    def method(self) -> Methods:
        return self.route.method

class Route:
    _CACHE: ClassVar[dict[str, Route]] = {}
    BASE: ClassVar[URL] = URL('https://discord.com/api/v8')

    __slots__ = ("method", "path")

    method: Methods
    path: str

    def __new__(cls, method: Methods, path: str) -> Route:
        path = path.lstrip("/")
        cache_bucket = method + ":" + path
        self = cls._CACHE.get(cache_bucket, None)

        if self is None:
            self = super().__new__(cls)
            self.method = method
            self.path = path
            cls._CACHE[cache_bucket] = self

        return self

    @property
    def url(self) -> URL | None:
        if "{" in self.path:
            # quick parameter check
            return None
        return self.BASE / self.path

    def with_params(self, **params) -> Endpoint:
        return Endpoint(self, params)

    def __mod__(self, params) -> Endpoint:
        return Endpoint(self, params)

class HTTPSession:
    def __init__(self, token: Token) -> None:
        headers = {
            "Authorization": token.get_auth(),
            "User-Agent": "Cordy (https://github.com/BytesToBits/Cordy, 0.1.0)"
        }

        self.session = ClientSession(headers=headers)

    def ws_connect(self, url: URL, **kwargs):
        return self.session.ws_connect(url, **kwargs)

    def request(self, endp: Endpoint | Route, **kwargs):
        if endp.url is None:
            raise ValueError(f"Used {type(endp)} instance with unformatted url")
        return self.session.request(endp.method, endp.url, **kwargs)

    async def get_gateway(self) -> URL:
        async with self.request(Route("GET", "/gateway")) as res:
            return URL((await res.json(loads=util.loads))["url"])

    async def get_gateway_bot(self) -> Msg:
        async with self.request(Route("GET", "/gateway/bot")) as resp:
            ret: Msg = await resp.json(loads=util.loads)
            return ret

    async def close(self):
        return await self.session.close()
