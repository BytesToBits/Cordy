from __future__ import annotations

from typing import Final

INC_MASK: Final[int] = 0xFFF
PROC_MASK: Final[int] = 0x1F << 12
WORKER_MASK: Final[int] = PROC_MASK << 5

DISCORD_EPOCH: Final[int] = 1420070400000

class Snowflake(int):
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
