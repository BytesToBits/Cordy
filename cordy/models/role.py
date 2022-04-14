from __future__ import annotations

from dataclasses import dataclass

from .permission import Permissions

from .snowflake import Resource, Snowflake
from ..types import Role as RoleP

# todo: Lets setup a cyclic refrence to guild
# instead of adding a ref to http session
@dataclass(eq=False)
class Role(Resource):
    __slots__ = (
        "name",
        "color",
        "display_seperate",
        "position",
        "permissions",
        "integration_managed",
        "mentionable",
        "icon",
        "emoji",
        "bot_id",
        "integration_id",
        "premium_subscriber"
    )
    name: str
    color: int
    display_seperate: bool
    position: int
    permissions: Permissions
    integration_managed: bool
    mentionable: bool
    icon: str | None
    emoji: str | None
    bot_id: Snowflake | None
    integration_id: Snowflake | None
    premium_subscriber: bool | None # None to indicate that tage are missing

    @classmethod
    def from_data(cls, data: RoleP):
        self = object.__new__(cls)
        Resource.__init__(self, data["id"])
        self.name = data["name"]
        self.color = data["color"]
        self.display_seperate = data["hoist"]
        self.position = data["position"]
        self.permissions = Permissions(data["permissions"])
        self.integration_managed = data["managed"]
        self.mentionable = data["mentionable"]

        self.icon = data.get("icon")
        self.emoji = data.get("unicode_emoji")

        tags = data.get("tags")
        if tags:
            try:
                self.bot_id = Snowflake(tags["bot_id"])
            except KeyError:
                self.bot_id = None

            try:
                self.integration_id = Snowflake(tags["integration_id"])
            except KeyError:
                self.integration_id = None

            self.premium_subscriber = "premium_subscriber" in tags
        else:
            self.bot_id = None
            self.integration_id = None
            self.premium_subscriber = None