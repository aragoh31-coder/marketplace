"""
Base service class for business logic
"""
from django.db import transaction
from django.core.cache import cache
import logging


class BaseService:
    """Base service class with common functionality"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @staticmethod
    def invalidate_cache(cache_keys):
        """Invalidate multiple cache keys"""
        if isinstance(cache_keys, str):
            cache_keys = [cache_keys]
        
        for key in cache_keys:
            cache.delete(key)
    
    def log_error(self, message, exc_info=None):
        """Log error with context"""
        self.logger.error(message, exc_info=exc_info, extra={
            'service': self.__class__.__name__
        })
    
    def log_info(self, message):
        """Log info message"""
        self.logger.info(message, extra={
            'service': self.__class__.__name__
        })
    
    @staticmethod
    def atomic_transaction(func):
        """Decorator for atomic database transactions"""
        def wrapper(*args, **kwargs):
            with transaction.atomic():
                return func(*args, **kwargs)
        return wrapper