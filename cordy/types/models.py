from __future__ import annotations

from typing import Literal, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Annotated
    IntAsStr = Annotated[str, "This is meant to be an int"]

class TotalUser(TypedDict):
    id: IntAsStr
    username: str
    discriminator: str
    avatar: str | None

class User(TotalUser, total=False):
    bot: bool
    system: bool
    banner: str | None
    accent_color: int | None
    flags: int
    public_flags: int

    # oauth only
    mfa_enabled: bool
    locale: str
    premium_type: int

    # needs email scope
    email: str | None
    verified : bool

class RoleTags(TypedDict, total=False):
    bot_id: IntAsStr
    integration_id: IntAsStr
    premium_subscriber: None # presence is the property

class TotalRole(TypedDict):
    id: IntAsStr
    name: str
    color: int
    hoist: bool
    position: int
    permissions: IntAsStr
    managed: bool
    mentionable: bool

class Role(TotalRole, total=False):
    icon: str | None
    unicode_emoji: str | None
    tags: RoleTags

class Overwrite(TypedDict):
    id: IntAsStr
    type: Literal[1, 0]
    allow: Annotated[IntAsStr, "The allowed permission bitset"]
    deny: Annotated[IntAsStr,
                    "The denied permission bitset,"
                    " each set bit represents a denied permission"]
    
class Emoji(TypedDict):
    id: IntAsStr
    name: str
    roles: list[IntAsStr] | None
    user: User | None
    require_colons: bool | None
    managed: bool | None
    animated: bool | None
    available: bool | None
