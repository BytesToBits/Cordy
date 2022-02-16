from __future__ import annotations

from .flags import Flag, IntFlags, populate_flags

__all__ = (
    "Intents",
)

@populate_flags
class Intents(IntFlags):
    guilds = Flag(1 << 0)
    """:class:`bool`: Wether guild related events are enabled"""

    members = Flag(1 << 1)
    """:class:`bool`: Wether guild member related events are enabled"""

    bans = Flag(1 << 2)
    """:class:`bool`: Wether guild bans related events are enabled"""

    emojis_and_stickers = Flag(1 << 3)
    """:class:`bool`: Wether guild emoji and sticker related events are enabled"""

    integrations = Flag(1 << 4)
    """:class:`bool`: Wether guild integrations related events are enabled"""

    webhooks = Flag(1 << 5)
    """:class:`bool`: Wether guild webhoks related events are enabled"""

    invites = Flag(1 << 6)
    """:class:`bool`: Wether guild invites related events are enabled"""

    voice_states = Flag(1 << 7)
    """:class:`bool`: Wether guild voice state related events are enabled"""

    presences = Flag(1 << 8)
    """:class:`bool`: Wether guild member presences related events are enabled"""


    guild_messages = Flag(1 << 9)
    """:class:`bool`: Wether guild messages related events are enabled"""

    guild_reactions = Flag(1 << 10)
    """:class:`bool`: Wether guild reactions related events are enabled"""

    guild_typing = Flag(1 << 11)
    """:class:`bool`: Wether guild typing related events are enabled"""


    dm_messages = Flag(1 << 12)
    """:class:`bool`: Wether dm messages related events are enabled"""

    dm_reactions = Flag(1 << 13)
    """:class:`bool`: Wether dm reactions related events are enabled"""

    dm_typing = Flag(1 << 14)
    """:class:`bool`: Wether dm typing related events are enabled"""


    messages = Flag((1 << 9) | (1 << 12))
    """:class:`bool`: Wether guild and dm message related events are enabled"""

    reactions = Flag((1 << 10) | (1 << 13))
    """:class:`bool`: Wether guild and dm reaction related events are enabled"""

    typing = Flag((1 << 11) | (1 << 14))
    """:class:`bool`: Wether guild and dm typing related events are enabled"""

    @classmethod
    def all(cls) -> Intents:
        """Create an Intents object with all instents enabled.

        Returns
        -------
        :class:`.Intents`
            The Intents object
        """
        inst = cls()
        inst.value = 2 ** cls._LEN_FLAGS - 1
        return inst

    @classmethod
    def privileged(cls) -> Intents:
        """Create an Intents object with only
        ``GUILD_PRESENCES`` & ``GUILD_MEMBERS`` intents enabled.

        Returns
        -------
        :class:`.Intents`
            The Intents object
        """
        inst = cls()
        inst.presences = True
        inst.members = True
        return inst

    @classmethod
    def default(cls) -> Intents:
        """Create an Intents object with all intents except privileged enabled.

        Returns
        -------
        :class:`.Intents`
            The Intents object
        """
        inst = cls.all()
        inst.presences = False
        inst.members = False
        return inst

    @classmethod
    def none(cls) -> Intents:
        """Create an Intents object with no intents enabled.

        Returns
        -------
        :class:`.Intents`
            The Intents object
        """
        return cls()
