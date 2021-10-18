import json
from typing import Any, Callable, Union

# Swappable json encoders and decoders to be used in the library
Json = Union[dict[str, Any], list[Union[dict[str, Any], Any]]]
Msg = dict[str, Any]

loads: Callable[[str], Any] = json.loads # Any allows custom type without cast
dumps: Callable[[Json], str] = json.dumps
