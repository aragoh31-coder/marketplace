"""
Core Architecture Package
Provides the foundation for the modular Django application.
"""

from .base import BaseModule, ModuleRegistry
from .decorators import dependency, module, service
from .exceptions import ModuleError, ServiceError
from .interfaces import ModuleInterface, ServiceInterface

__all__ = [
    "BaseModule",
    "ModuleRegistry",
    "ModuleInterface",
    "ServiceInterface",
    "module",
    "service",
    "dependency",
    "ModuleError",
    "ServiceError",
]
