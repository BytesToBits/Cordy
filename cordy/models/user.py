from __future__ import annotations

from .flags import FrozenFlag as FF
from .flags import FrozenFlags


class UserFlags(FrozenFlags):
    staff = FF(1)
    """:class:`bool`: A discord employee"""
    partner = FF(1 << 1)
    """:class:`bool`: Owner of a partnered server"""
    hypesquad_events = FF(1 << 2)
    """:class:`bool`: HypeSquad events coordinator"""
    bug_hunter_level_1 = FF(1 << 3)
    """:class:`bool`: Bug hunter level 1"""
    # 4, 5 missing

    hypesquad_bravery = FF(1 << 6)
    """:class:`bool`: HypeSquad Bravery house member"""
    hypesquad_brilliance = FF(1 << 7)
    """:class:`bool`: HypeSquad Brilliance house member"""
    hypesquad_balance = FF(1 << 8)
    """:class:`bool`: HypeSquad Balance house member"""

    early_supporter = FF(1 << 9)
    """:class:`bool`: Early nitro supporter"""
    team_user = FF(1 << 10)
    """:class:`bool`: User is a team"""
    #11, 12, 13
    bug_hunter_level_2 = FF(1 << 14)
    """:class:`bool`: Bug Hunter level 2"""
    bug_hunter = FF(1 << 3 | 1 << 14)
    """:class:`bool`: Bug Hunter level 1 or 2"""
    # 15
    verified_bot = FF(1 << 16)
    """:class:`bool`: Verfied bot account"""
    verified_dev = FF(1 << 17)
    """:class:`bool`: Early verified bot developer"""
    certified_mod = FF(1 << 18)
    """:class:`bool`: Discord certified moderator"""
    interaction_bot = FF(1 << 19)
    """:class:`bool`: The bot exclusively uses http interactions"""
