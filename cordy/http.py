from yarl import URL

from typing import ClassVar

__all__ = (
    "Route"
)

class Route:
    BASE: ClassVar[URL] = URL('https://discord.com/api/v8')

    def __init__(self):
        ...