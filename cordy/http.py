from __future__ import annotations

from yarl import URL

from typing import ClassVar

__all__ = (
    "Route"
)

# TODO: Make buckets for ratelimits
# MAYBE: Remove cache if global instances are used

class Endpoint:
    __slots__ = ("route", "url")

    route: Route
    url: URL

    def __init__(self, route: Route, params: dict[str, str]) -> None:
        self.route = Route
        self.url = self.route.BASE / route.path.format_map(params)

    @property
    def method(self) -> str:
        return self.route.method

class Route:
    _CACHE: ClassVar[dict[str, Route]] = {}
    BASE: ClassVar[URL] = URL('https://discord.com/api/v8')

    __slots__ = ("method", "path")

    def __new__(cls, method: str, path: str) -> Route:
        cache_bucket = method + ":" + path
        self = cls._CACHE.get(cache_bucket, None)

        if self is None:
            self = super().__new__(cls, method, path)
            self.method = method
            self.path = path
            cls._CACHE[cache_bucket] = self

        return self

    def __call__(self, **params) -> Endpoint:
        return Endpoint(self, params)
