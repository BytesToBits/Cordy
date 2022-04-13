from __future__ import annotations

from typing import Final
import datetime

INC_MASK: Final[int] = 0xFFF
PROC_MASK: Final[int] = 0x1F << 12
WORKER_MASK: Final[int] = PROC_MASK << 5

DISCORD_EPOCH: Final[int] = 1420070400000

class Snowflake(int):
    __slots__ = ()

    @property
    def proc_inc_id(self) -> int:
        return self & INC_MASK

    @property
    def proc_id(self) -> int:
        return (self & PROC_MASK) >> 12

    @property
    def worker_id(self) -> int:
        return (self & WORKER_MASK) >> 17

    @property
    def timestamp_ms(self) -> int:
        return (self >> 22) + DISCORD_EPOCH

    @property
    def timestamp(self) -> float:
        return ((self >> 22) + DISCORD_EPOCH) / 1000

    @property
    def created_at(self) -> datetime.datetime: # may raise OverflowError
        return datetime.datetime.utcfromtimestamp(self.timestamp)

# Base class for discord entities
class Resource:
    id: Snowflake

    __slots__ = ("id",)

    def __init__(self, id: int):
        self.id = Snowflake(id)

    def __repr__(self) -> str:
        return f"Resource(id={self.id})"

    def __format__(self, spec: str):
        if not spec:
            return str(self)

        spec = spec.lstrip("(").rstrip(")")
        parts = spec.split(":", 1)

        try:
            # todo: change to use formatting attribute/names specific to formatting
            # maybe implement with __getattr__ in each subclass?
            attr = getattr(self, parts[0])
        except AttributeError as err:
            raise ValueError(f"Unexpected format attribute: {parts[0]!r}") from err

        if len(parts) == 1:
            return str(attr)

        return format(attr, parts[1])

    def __hash__(self):
        return hash(self.id)

    def __index__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id
