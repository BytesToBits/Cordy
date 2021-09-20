from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Intents

if TYPE_CHECKING:
    from aiohttp import ClientWebSocketResponse

class GateWay:
    def __init__(self, ws: ClientWebSocketResponse, token: str, *, intents: Intents = None) -> None:
        self.ws = ws
        self.token = token
        self.intents = intents or Intents.default()

class Shard:
    connection: GateWay
    ...
