from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal

from aiohttp import ClientSession
from yarl import URL

if TYPE_CHECKING:
    from .client import Client

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

    def with_params(self, **params) -> Endpoint:
        return Endpoint(self, params)

    def __mod__(self, params) -> Endpoint:
        return Endpoint(self, params)

class HTTPSession:
    headers: dict[str, str]

    def __init__(self, session: ClientSession, client: Client) -> None:
        self.session = session

        self.headers = {
            "Authorization": client.token.get_auth(),
            "User-Agent": "Cordy (https://github.com/BytesToBits/Cordy, 0.1.0)"
        }

    async def ws_connect(self, url: URL, **kwargs):
        kwargs.setdefault("headers", self.headers)
        kwargs["headers"].update(self.headers)

        return await self.session.ws_connect(url, **kwargs)

    async def request(self, endp: Endpoint, **kwargs):
        kwargs.setdefault("headers", self.headers)
        kwargs["headers"].update(self.headers)

        return await self.session.request(endp.method, endp.url, **kwargs)

    async def close(self):
        return await self.session.close()
