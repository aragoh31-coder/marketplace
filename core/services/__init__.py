"""
Core Services Package
Provides service layer functionality for the modular system.
"""

from .service_registry import ServiceRegistry
from .base_service import BaseService
from .service_manager import ServiceManager

__all__ = [
    'ServiceRegistry',
    'BaseService', 
    'ServiceManager'
]