from importlib.metadata import version

from .auth import *
from .client import *
from .errors import *
from .models import *

__all__ = (
    *auth.__all__,
    *client.__all__,
    *errors.__all__,
    *models.__all__
)

__version__ = version("cordy")
del version
