from __future__ import annotations

from typing import TypedDict

class TotalUser(TypedDict):
    id: int
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