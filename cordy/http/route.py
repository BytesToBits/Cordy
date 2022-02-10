from __future__ import annotations

from typing import ClassVar, Final, Literal, final, overload

from yarl import URL
from dataclasses import dataclass

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

# don't really remember why this is a dict?
PARAMS: Final[dict[Parameters, None]] = dict.fromkeys(Parameters.__args__) # type: ignore[attr-defined]

@final
class Endpoint:
    __slots__ = ("route", "url", "params")

    route: Route
    url: URL

    def __init__(self, route: Route, params: dict[Parameters, int | str]) -> None:
        self.route = route

        try:
            # ignore because we are handling invalid key
            self.url = self.route.BASE / route.path.format_map(params) # type: ignore[arg-type]
        except KeyError as err:
            raise ValueError("All arguments needed for route not provided") from err

        self.params = tuple(params.get(k) for k in PARAMS)

    @property
    def method(self) -> Methods:
        return self.route.method

    @property
    def param_hash(self) -> str:
        return '-'.join(str(v) for v in self.params)

# Composed of immutable types, and freezing just
# for hashes is an overkill.
@final
@dataclass(init=False, unsafe_hash=True)
class Route:
    method: Methods
    path: str

    _CACHE: ClassVar[dict[str, Route]] = {}
    BASE: Final = URL(f'https://discord.com/api/v{API_VERSION}')

    __slots__ = ("method", "path")

    def __new__(cls, method: Methods, path: str) -> Route:
        path = path.lstrip("/")
        cache_bucket = method + ":" + path
        self = cls._CACHE.get(cache_bucket, None)

        if self is not None:
            return self
        else:
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

    @property
    def route(self) -> Route:
        return self

    @overload
    def with_params(self) -> Endpoint:
        ...

    @overload
    def with_params(self, *,
                    channel_id: int = ...,
                    guild_id: int = ...,
                    webhook_id: int = ...,
                    webhook_token: str = ...) -> Endpoint:
        ...

    def with_params(self, **params):
        return Endpoint(self, params) # type: ignore[arg-type] # because overload provided

    def __mod__(self, params: dict[Parameters | str, int | str]) -> Endpoint:
        return Endpoint(self, params) # type: ignore
