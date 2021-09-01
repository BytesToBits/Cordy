from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Intents

__all__ = (
    'Client'
)

class Client:
    def __init__(self, intents: Optional[Intents]):
        ...

    def connect(self, token: str) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def reconnect(self) -> None:
        ...