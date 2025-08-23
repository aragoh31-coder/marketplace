"""
Base Service Class
Provides the foundation for all services in the system.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Base class for all services in the system.
    Services provide business logic and external integrations.
    """

    # Service metadata
    service_name: str = None
    version: str = "1.0.0"
    description: str = ""
    author: str = ""

    # Service configuration
    config: Dict[str, Any] = {}
    cache_timeout: int = 300  # 5 minutes default
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds

    # Service state
    _initialized: bool = False
    _healthy: bool = True
    _last_health_check: float = 0
    _health_check_interval: float = 60  # seconds

    def __init__(self, **kwargs):
        """Initialize the service with configuration."""
        self.config = kwargs
        self._initialized = False
        self._healthy = True
        self._last_health_check = 0

        # Validate service configuration
        self._validate_config()

        # Initialize the service
        self._initialize()

    def _validate_config(self):
        """Validate service configuration."""
        if not self.service_name:
            raise ValueError(f"Service {self.__class__.__name__} must have a service_name")

        # Check required configuration
        required_config = self.get_required_config()
        for key in required_config:
            if key not in self.config:
                raise ValueError(f"Service {self.service_name} requires config: {key}")

    def _initialize(self):
        """Internal initialization method."""
        try:
            if self.initialize():
                self._initialized = True
                logger.info(f"Service {self.service_name} initialized successfully")
            else:
                logger.error(f"Service {self.service_name} failed to initialize")
        except Exception as e:
            logger.error(f"Service {self.service_name} initialization error: {e}")
            self._healthy = False

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the service. This is where you set up connections,
        validate configuration, etc.
        """
        pass

    @abstractmethod
    def cleanup(self) -> bool:
        """
        Clean up the service. This is where you close connections,
        clean up resources, etc.
        """
        pass

    def get_required_config(self) -> List[str]:
        """Get list of required configuration keys."""
        return []

    def get_optional_config(self) -> List[str]:
        """Get list of optional configuration keys."""
        return []

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value

    def is_available(self) -> bool:
        """Check if the service is available."""
        return self._initialized and self._healthy

    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        current_time = time.time()

        # Check if we need to perform a health check
        if current_time - self._last_health_check > self._health_check_interval:
            self._perform_health_check()
            self._last_health_check = current_time

        return {
            "service_name": self.service_name,
            "version": self.version,
            "healthy": self._healthy,
            "initialized": self._initialized,
            "last_health_check": self._last_health_check,
            "config_keys": list(self.config.keys()),
            "cache_enabled": hasattr(self, "cache_timeout") and self.cache_timeout > 0,
        }

    def _perform_health_check(self):
        """Perform a health check on the service."""
        try:
            self._healthy = self.health_check()
        except Exception as e:
            logger.error(f"Health check failed for {self.service_name}: {e}")
            self._healthy = False

    def health_check(self) -> bool:
        """
        Perform a health check. Override this method to implement
        custom health checking logic.
        """
        return self._initialized

    def get_cache_key(self, key: str) -> str:
        """Generate a cache key for this service."""
        return f"service:{self.service_name}:{key}"

    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get a cached value."""
        if self.cache_timeout <= 0:
            return default

        cache_key = self.get_cache_key(key)
        return cache.get(cache_key, default)

    def set_cached(self, key: str, value: Any, timeout: int = None) -> bool:
        """Set a cached value."""
        if self.cache_timeout <= 0:
            return False

        cache_key = self.get_cache_key(key)
        cache_timeout = timeout or self.cache_timeout

        try:
            cache.set(cache_key, value, cache_timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to cache value for {self.service_name}: {e}")
            return False

    def clear_cache(self, key: str = None) -> bool:
        """Clear cached values."""
        try:
            if key:
                cache_key = self.get_cache_key(key)
                cache.delete(cache_key)
            else:
                # Clear all cached values for this service
                # This is a simple implementation - in production you might want
                # to use cache versioning or pattern-based deletion
                pass
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache for {self.service_name}: {e}")
            return False

    def retry_operation(self, operation: callable, *args, **kwargs) -> Any:
        """
        Retry an operation with exponential backoff.

        Args:
            operation: The operation to retry
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            The result of the operation

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self.retry_attempts):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Operation failed for {self.service_name}, attempt {attempt + 1}/{self.retry_attempts}, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Operation failed for {self.service_name} after {self.retry_attempts} attempts: {e}")

        raise last_exception

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics. Override to provide custom metrics."""
        return {
            "service_name": self.service_name,
            "version": self.version,
            "healthy": self._healthy,
            "initialized": self._initialized,
            "cache_hits": 0,  # Override to track actual cache hits
            "cache_misses": 0,  # Override to track actual cache misses
            "request_count": 0,  # Override to track actual requests
            "error_count": 0,  # Override to track actual errors
        }

    def log_operation(self, operation: str, details: Dict[str, Any] = None, level: str = "info"):
        """Log an operation for monitoring purposes."""
        log_data = {
            "service": self.service_name,
            "operation": operation,
            "timestamp": time.time(),
        }

        if details:
            log_data.update(details)

        log_method = getattr(logger, level, logger.info)
        log_method(f"Service operation: {log_data}")

    def __str__(self):
        return f"{self.service_name} v{self.version}"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.service_name}>"
