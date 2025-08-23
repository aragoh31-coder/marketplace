"""
Base Service Class
Provides the foundation for all services in the system.
"""

import logging
import time
import weakref
from abc import ABC, abstractmethod
from functools import lru_cache, wraps
from typing import Any, Dict, List, Optional, Type, Union
from threading import RLock
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache
from django.db import connections, transaction
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


def performance_monitor(func):
    """Decorator to monitor service method performance."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.perf_counter() - start_time
            self._record_performance_metric(func.__name__, execution_time, True)
            return result
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            self._record_performance_metric(func.__name__, execution_time, False)
            raise
    return wrapper


def cache_result(timeout: int = 300, key_func=None):
    """Decorator to cache service method results."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if key_func:
                cache_key = f"{self.service_name}:{func.__name__}:{key_func(*args, **kwargs)}"
            else:
                cache_key = f"{self.service_name}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache first
            result = self.get_cached(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(self, *args, **kwargs)
            self.set_cached(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


class ConnectionPool:
    """Simple connection pool for database connections."""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._pool = []
        self._lock = RLock()
    
    @contextmanager
    def get_connection(self, alias='default'):
        """Get a database connection from the pool."""
        with self._lock:
            try:
                conn = connections[alias]
                yield conn
            finally:
                # Connection is automatically returned to Django's pool
                pass


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
    
    # Performance settings
    max_batch_size: int = 1000
    query_timeout: int = 30
    connection_pool_size: int = 10
    
    # Service state
    _initialized: bool = False
    _healthy: bool = True
    _last_health_check: float = 0
    _health_check_interval: float = 60  # seconds
    _performance_metrics: Dict[str, List[float]] = {}
    _lock = RLock()
    
    # Class-level caches
    _instance_cache = weakref.WeakValueDictionary()
    _query_cache = {}

    def __init__(self, **kwargs):
        """Initialize the service with configuration."""
        self.config = kwargs
        self._initialized = False
        self._healthy = True
        self._last_health_check = 0
        self._performance_metrics = {}
        self._connection_pool = ConnectionPool(self.connection_pool_size)
        
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

    @cached_property
    def cache_prefix(self) -> str:
        """Get cache key prefix for this service."""
        return f"service:{self.service_name}"

    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get value from cache with error handling."""
        try:
            full_key = f"{self.cache_prefix}:{key}"
            return cache.get(full_key, default)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return default

    def set_cached(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set value in cache with error handling."""
        try:
            full_key = f"{self.cache_prefix}:{key}"
            timeout = timeout or self.cache_timeout
            cache.set(full_key, value, timeout)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False

    def clear_cache(self, key: str = None) -> bool:
        """Clear cache entries."""
        try:
            if key:
                full_key = f"{self.cache_prefix}:{key}"
                cache.delete(full_key)
            else:
                # Clear all cache entries for this service
                cache.delete_pattern(f"{self.cache_prefix}:*")
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False

    @contextmanager
    def get_db_connection(self, alias='default'):
        """Get database connection with connection pooling."""
        with self._connection_pool.get_connection(alias) as conn:
            yield conn

    def execute_query(self, query: str, params: List = None, alias='default') -> List[Dict]:
        """Execute optimized database query."""
        with self.get_db_connection(alias) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or [])
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute_batch_query(self, queries: List[tuple], alias='default') -> bool:
        """Execute multiple queries in a batch."""
        try:
            with self.get_db_connection(alias) as conn:
                with transaction.atomic(using=alias):
                    with conn.cursor() as cursor:
                        for query, params in queries:
                            cursor.execute(query, params or [])
            return True
        except Exception as e:
            logger.error(f"Batch query execution failed: {e}")
            return False

    def _record_performance_metric(self, method_name: str, execution_time: float, success: bool):
        """Record performance metrics for monitoring."""
        with self._lock:
            if method_name not in self._performance_metrics:
                self._performance_metrics[method_name] = []
            
            metric_data = {
                'execution_time': execution_time,
                'success': success,
                'timestamp': time.time()
            }
            
            # Keep only last 100 metrics per method
            self._performance_metrics[method_name].append(metric_data)
            if len(self._performance_metrics[method_name]) > 100:
                self._performance_metrics[method_name] = self._performance_metrics[method_name][-100:]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this service."""
        with self._lock:
            metrics = {}
            for method_name, method_metrics in self._performance_metrics.items():
                if method_metrics:
                    avg_time = sum(m['execution_time'] for m in method_metrics) / len(method_metrics)
                    success_rate = sum(1 for m in method_metrics if m['success']) / len(method_metrics)
                    metrics[method_name] = {
                        'avg_execution_time': avg_time,
                        'success_rate': success_rate,
                        'total_calls': len(method_metrics)
                    }
            return metrics

    def retry_on_failure(self, func, *args, **kwargs):
        """Retry function execution on failure."""
        last_exception = None
        for attempt in range(self.retry_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
        
        raise last_exception

    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        current_time = time.time()
        if current_time - self._last_health_check > self._health_check_interval:
            self._health_check()
            self._last_health_check = current_time
        return self._healthy

    def _health_check(self):
        """Perform health check."""
        try:
            # Basic health check - override in subclasses for specific checks
            self._healthy = self._initialized
        except Exception as e:
            logger.error(f"Health check failed for service {self.service_name}: {e}")
            self._healthy = False

    def get_service_health(self) -> Dict[str, Any]:
        """Get detailed service health information."""
        return {
            'service_name': self.service_name,
            'version': self.version,
            'healthy': self.is_healthy(),
            'initialized': self._initialized,
            'last_health_check': self._last_health_check,
            'performance_metrics': self.get_performance_metrics()
        }

    def is_available(self) -> bool:
        """Check if service is available for use."""
        return self._initialized and self.is_healthy()

    @classmethod
    def get_instance(cls, **kwargs) -> 'BaseService':
        """Get singleton instance of service."""
        key = f"{cls.__name__}:{hash(str(kwargs))}"
        if key not in cls._instance_cache:
            cls._instance_cache[key] = cls(**kwargs)
        return cls._instance_cache[key]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.service_name}, healthy={self.is_healthy()})>"
