from __future__ import annotations

from typing import ClassVar, Literal, Union

__all__ = (
    "Flag",
    "IntFlags"
)

AnyBitLike = Union[bool, Literal[1, 0]]

def populate_flags(cls):
    cls.FLAGS = {
        name.lower(): flag.value for name, flag in cls.__dict__.items() if isinstance(flag, Flag)
    }

    cls._LEN_FLAGS =  max(cls.FLAGS.values()).bit_length()

    return cls

class Flag:
    __slots__ = ("value",)

    value: int

    def __init__(self, value: int):
        self.value = value

    def __get__(self, inst: IntFlags, _) -> bool:
        return (inst.value & self.value) == self.value

    def __set__(self, inst, value: AnyBitLike) -> None:
        inst.value = (inst.value & ~self.value) | (self.value * (value & 1))

class IntFlags: # For intents
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

class FrozenFlags(int): # Read-Only, for user flags
    def __new__(cls, data: int = None):
        if data is not None:
            return super().__new__(cls, data)

    def __getitem__(self, index: int) -> bool:
        return bool(self & (1 << index))

class FrozenFlag:
    __slots__ = ("value",)

    value: int

    def __init__(self, value: int):
        self.value = value

    def __set__(self, inst: FrozenFlags, _):
        raise TypeError("Cannot set value for a FrozenFlag instance")

    def __get__(self, inst: FrozenFlags, _) -> bool:
        return bool(inst & self.value)


