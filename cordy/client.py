from .models import Intents

from typing import Optional

__all__ = (
    'Client'
)

class Client:
    def __init__(self, intents: Optional[Intents]):
        ...

    def connect(self, token):
        ...

    def disconnect(self):
        ...

    def reconnect(self):
        ...