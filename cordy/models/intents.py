from  __future__ import annotations

from typing import ClassVar, Literal, Union

__all__ = (
    "Intents",
)


AnyBitLike = Union[bool, Literal[1, 0]]

def populate_flags(cls):
    cls.FLAGS = {
        name.lower(): flag.value for name, flag in cls.__dict__.items() if isinstance(flag, Flag)
    }

    cls._LEN_FLAGS =  max(cls.FLAGS.values()).bit_length()

    return cls

class Flag:
    value: int

    def __init__(self, value: int):
        self.value = value

    def __get__(self, inst: IntFlags, _) -> bool:
        return (inst.value & self.value) == self.value

    def __set__(self, inst, value: AnyBitLike) -> None:
        inst.value = (inst.value & ~self.value) | (self.value * (value & 1))

class IntFlags:
    FLAGS: ClassVar[dict[str, int]]
    _LEN_FLAGS: ClassVar[int]

    value: int

    def __init__(self, **kwargs: dict[str, bool]) -> None:
        self.value = 0 # start from all disabled

        for k, v in kwargs.items():
            if v:
                try:
                    self.value |= self.FLAGS[k]
                except KeyError:
                    raise TypeError(f"Unexpected flag keyword argument: {k}")

    def __setitem__(self, index: int, value: AnyBitLike) -> None:
        if index >= self._LEN_FLAGS:
            raise IndexError (f"Index out of range for {type(self)} object.")
        mask = 1 << index
        self.value = (self.value & ~mask) | ((value << index) & mask)

    def __getitem__(self, index: int) -> bool:
        return bool((self.value & (1 << index)))

    def __or__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError(f"unsupported operand type(s) for |: '{type(self)}' and '{type(other)}'")

        inst = self.__class__()
        inst.value = self.value | other.value
        return inst

    def __ior__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError(f"unsupported operand type(s) for |: '{type(self)}' and '{type(other)}'")

        self.value |= other.value

    @classmethod
    def from_int(cls, value: int):
        inst = cls()
        inst.value = value
        return cls


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
