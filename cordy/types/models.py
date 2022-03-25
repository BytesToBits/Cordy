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
    mfa_enables: bool
    banner: str | None
    accent_color: int | None
    locale: str
    flags: int
    premium_type: int
    public_flags: int

    # needs email scope
    email: str | None
    verified : bool