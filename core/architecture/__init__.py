"""
Core Architecture Package
Provides the foundation for the modular Django application.
"""

from .base import BaseModule, ModuleRegistry
from .interfaces import ModuleInterface, ServiceInterface
from .decorators import module, service, dependency
from .exceptions import ModuleError, ServiceError

__all__ = [
    'BaseModule',
    'ModuleRegistry', 
    'ModuleInterface',
    'ServiceInterface',
    'module',
    'service',
    'dependency',
    'ModuleError',
    'ServiceError'
]