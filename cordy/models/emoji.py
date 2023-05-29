from __future__ import annotations

from dataclasses import dataclass

from .snowflake import Resource, Snowflake
from ..types import Emoji as EmojiP
from . import BaseUser

BUILTIN_ID = Snowflake(-1)

@dataclass
class Emoji(Resource):
    __slots__ = (
        "name",
        "roles",
        "user",
        "require_colons",
        "managed",
        "animated",
        "available"
    )

    name: str | None
    roles: list[Snowflake] | None
    user: BaseUser | None
    require_colons: bool | None
    managed: bool | None
    animated: bool | None
    available: bool | None

    @classmethod
    def from_data(cls, data: EmojiP):
        self = object.__new__(cls)
        self.name = data["name"]
        _id = data["id"]

        if _id is None:
            self.id = BUILTIN_ID
        else:
            self.id = Snowflake(_id)

        _roles = data.get("roles")

        if _roles is not None:
            self.roles = list(Snowflake(i) for i in _roles)
        else:
            self.roles = None

        _user = data.get("user")

        if _user is not None:
            self.user = BaseUser.from_data(_user)
        else:
            self.user = None

        self.require_colons = data.get("require_colons")
        self.managed = data.get("managed")
        self.animated = data.get("animated")
        self.available = data.get("available")

    @property
    def is_builtin(self):
        """:class:`bool`: Whether emoji is a builtin unicode emoji"""
        return self.id is BUILTIN_ID

    # TODO: support str