# backend package initialization
"""
Insurance Report Generator Backend Package
"""

from . import api
from . import models
from . import services
from . import utils
from . import config
from . import middleware
from . import tasks

__version__ = "1.0.0"

# Auto-generated __init__.py file for backend package
from .main import app

__all__ = [
    "api",
    "models",
    "services",
    "utils",
    "config",
    "middleware",
    "tasks",
    "app",
]
