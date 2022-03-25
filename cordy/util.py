from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Union
import inspect
from time import perf_counter
from itertools import chain

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

__all__ = (
    "Json",
    "Msg",
    "loads", "dumps",
    "make_proxy_for"
)

# Swappable json encoders and decoders to be used in the library
Json = dict[str, Any]
Msg = dict[str, Any]

loads: Callable[[str], Any] = json.loads # Any allows custom type without cast
dumps: Callable[[Json], str] = lambda dat: json.dumps(dat, separators=(',', ':'))

def make_proxy_for(org_cls, /, *, attr: str, proxied_attrs: Iterable[str] | None = None, proxied_methods: Iterable[str] | None = None):
    def deco(cls):
        def make_encapsulators(name: str):
            nonlocal attr

            def fset(_, _1, _2):
                raise TypeError(f"Cannot mutate attribute '{name}' on a {cls} instance")

            def fdel(_, _1):
                raise TypeError(f"Cannot delete attribute '{name}' on a {cls} instance")

            return {
                "fget": lambda s: getattr(s, "name"),
                "fset": fset,
                "fdel": fdel
            }

        proxied = chain(
            proxied_attrs or chain.from_iterable(
                getattr(c, '__slots__', tuple()) for c in org_cls.__mro__
            ),
            proxied_methods or filter(
                lambda m: not hasattr(cls, m),
                map(
                    lambda m: m[0], inspect.getmembers(org_cls, predicate=inspect.isfunction)
                )
            )
        )


        for s in proxied:
            setattr(cls, s, property(**make_encapsulators(s)))

        return cls
    return deco

class Timer:
    """A real time timer.
    """
    __slots__ = ("_time",)

    _time: float | None

    def __init__(self) -> None:
        self._time = None

    def start(self):
        self._time = perf_counter()
        return self

    def stop(self) -> float:
        try:
            return self._time - perf_counter() # type: ignore
        except TypeError:
            raise ValueError("Cannot stop a timer which has not been started.")
        finally:
            self._time = None
