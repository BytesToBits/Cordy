from __future__ import annotations

from typing import Union

class Token:
    BOT_PREFIX = "Bot"
    BEARER_PREFIX = "Bearer"

    def __init__(self, token: str, bot: bool = False):
        self.bot = bot
        self.bearer = not bot

        self.token = token

    def get_auth(self) -> str:
        if self.bot:
            return self.BOT_PREFIX + " " + self.token
        else:
            return self.BEARER_PREFIX + " " + self.token

    @classmethod
    def from_auth(cls, auth: str) -> Token:
        try:
            type_, token = auth.strip().split()
        except ValueError as err:
            raise ValueError("Invalid header auth value received.") from err

        cls(token, type_.lower() == cls.BOT_PREFIX.lower(), )

StrOrToken = Union[str, Token]
