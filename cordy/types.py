from __future__ import annotations

from typing import Literal, TypedDict

from .util import Msg

class Payload(TypedDict):
    op: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    d: Msg | None
    s: int | None
    t: str | None

class Dispatch(TypedDict):
    op: Literal[0]
    d: Msg | None
    s: int
    t: str
