from __future__ import annotations

from typing import Literal, TypedDict, Union

from cordy.util import Msg

MayBeInt = Union[int, None]

class Payload(TypedDict):
    op: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    d: Msg | None
    s: int | None
    t: str | None


class Dispatch(TypedDict):
    op: Literal[0]
    d: Msg | None
    s: MayBeInt
    t: str

class Heartbeat(TypedDict):
    op: Literal[1]
    d: MayBeInt
    s: None
    t: None

class InvalidSession(TypedDict):
    op: Literal[9]
    d: bool
    s: None
    t: None

class Hello(TypedDict):
    op: Literal[10]
    d: dict[Literal["heartbeat_interval"], float]
    s: None
    t: None

class HeartBeatAck(TypedDict):
    op: Literal[11]
    d: None
    s: None
    t: None
