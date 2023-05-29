from importlib.metadata import version

from .auth import *
from .client import *
from .errors import *
from .models import *
from .gateway import *
from .runner import *

try:
    __version__ = version("cordy.py")
except:
    __version__ = "0.2.dev0"

del version
