from importlib.metadata import version

from .auth import *
from .client import *
from .errors import *
from .models import *

__version__ = version("cordy")
del version
