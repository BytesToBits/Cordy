from __future__ import annotations

from typing import ClassVar, Union

__all__ = (
    "Token",
)

class Token:
    """Represents an API token.

    Only Bot and Bearer Tokens are supported.
    User tokens are not supported

    Attributes
    ----------
    token : :class:`str`
        The token string without any prefixes like "Bot" or "Bearer"
    bearer : :class:`bool`
        Whether the token is an oauth bearer token. This is always the negation of :attr:`.Token.bot`
    """
    BOT_PREFIX: ClassVar[str] = "Bot"
    BEARER_PREFIX: ClassVar[str] = "Bearer"

    _bot: bool
    token: str

    def __init__(self, token: str, bot: bool = False):
        self._bot = bot
        self.token = token

    def get_auth(self) -> str:
        """Return the authorization header for the token

        Returns
        -------
        :class:`str`
            The authorization header value.
        """
        if self.bot:
            return self.BOT_PREFIX + " " + self.token
        else:
            return self.BEARER_PREFIX + " " + self.token

    @property
    def bot(self) -> bool:
        """:class:`bool` : Whether the token is a bot token"""
        return self._bot

    @property
    def bearer(self) -> bool:
        """:class:`bool` : Whether the token is an oauth bearer token.
        This is always the negation of :attr:`.Token.bot`
        """
        return not self._bot

    @classmethod
    def from_auth(cls, auth: str) -> Token:
        """Build a :class:`.Token` from an auth header format.

        Parameters
        ----------
        auth : :class:`str`
            The authorization header format string.

        Returns
        -------
        :class:`.Token`
            The token built from the auth header value.

        Raises
        ------
        :exc:`ValueError`
            Format of the auth parameter is incorrect.
        """
        try:
            type_, token = auth.strip().split()
        except ValueError as err:
            raise ValueError("Invalid header auth value received.") from err

        return cls(token, type_.lower() == cls.BOT_PREFIX.lower())

StrOrToken = Union[str, Token]
