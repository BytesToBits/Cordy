from importlib.metadata import version

from .client import Client
from .models import Intents


__version__ = version("cordy")
del version
