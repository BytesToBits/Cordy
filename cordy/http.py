from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final, Literal, final, overload

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

API_VERSION: Final[int] = 8
API_PATH: Final[str] = f"/api/v{API_VERSION}"

# TODO: Make buckets for ratelimits
# MAYBE: Remove cache if global instances are used
Methods = Literal["GET", "PUT", "PATCH", "POST", "DELETE"]
Parameters = Literal['channel_id', 'guild_id', 'webhook_id', 'webhook_token']

PARAMS: Final[set[str]] = set(Parameters.__args__) # type: ignore[attr-defined]

@final
class Endpoint:
    __slots__ = ("route", "url", "bucket")

    route: Route # TOREMOVE: Change to method instead
    url: URL
    bucket: str

    def __init__(self, route: Route, params: dict[Parameters, int | str]) -> None:
        self.route = route

        try:
            # ignore because we are handling invalid key
            self.url = self.route.BASE / route.path.format_map(params) # type: ignore[arg-type]
        except KeyError as err:
            raise ValueError("All arguments needed for route not provided") from err

        self.bucket  = (self.method
                        + " "
                        + '-'.join(str(v) for k, v in params.items() if k in PARAMS)
                        + " "
                        + self.route.path)

    @property
    def method(self) -> Methods:
        return self.route.method

@final
class Route:
    _CACHE: ClassVar[dict[str, Route]] = {}
    BASE: ClassVar[URL] = URL(f'https://discord.com/api/v{API_VERSION}')

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

    @overload
    def with_params(self) -> Endpoint:
        ...

    @overload
    def with_params(self,
                    channel_id: int = ...,
                    guild_id: int = ...,
                    webhook_id: int = ...,
                    webhook_token: str = ...) -> Endpoint:
        ...

    def with_params(self, **params):
        return Endpoint(self, params) # type: ignore[arg-type] # because overload provided

    def __mod__(self, params: dict[Parameters, int | str]) -> Endpoint:
        return Endpoint(self, params)

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
