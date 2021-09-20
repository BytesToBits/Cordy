import json
from typing import Any, Callable, Union

# Swappable json encoders and decoders to be used in the library
Json = Union[dict[str, Any], list[dict[str, Any], Any]]

loads: Callable[[str], Json] = json.loads
dumps: Callable[[Json], str] = json.dumps
