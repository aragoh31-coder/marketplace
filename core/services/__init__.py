"""
Core Services Package
Provides service layer functionality for the modular system with optimized lazy loading.
"""

import importlib
from typing import Dict, Type, Optional, Any
import threading


class LazyServiceLoader:
    """Lazy loader for services to reduce startup time and memory usage."""
    
    def __init__(self):
        self._services_cache: Dict[str, Type] = {}
        self._lock = threading.RLock()
        
        # Service registry with module paths
        self._service_registry = {
            'BaseService': 'core.services.base_service',
            'ServiceRegistry': 'core.services.service_registry',
            'ServiceManager': 'core.services.service_manager',
            'UserService': 'core.services.user_service',
            'WalletService': 'core.services.wallet_service',
            'VendorService': 'core.services.vendor_service',
            'ProductService': 'core.services.product_service',
            'OrderService': 'core.services.order_service',
            'DisputeService': 'core.services.dispute_service',
            'MessagingService': 'core.services.messaging_service',
            'SupportService': 'core.services.support_service',
        }
    
    def __getattr__(self, name: str) -> Type:
        """Lazy load service classes when accessed."""
        if name not in self._service_registry:
            raise AttributeError(f"Service '{name}' not found")
        
        with self._lock:
            if name not in self._services_cache:
                module_path = self._service_registry[name]
                module = importlib.import_module(module_path)
                service_class = getattr(module, name)
                self._services_cache[name] = service_class
            
            return self._services_cache[name]
    
    def get_available_services(self) -> list:
        """Get list of available service names."""
        return list(self._service_registry.keys())
    
    def preload_service(self, service_name: str) -> None:
        """Preload a specific service."""
        if service_name in self._service_registry:
            getattr(self, service_name)
    
    def preload_all(self) -> None:
        """Preload all services (use sparingly)."""
        for service_name in self._service_registry:
            self.preload_service(service_name)


# Create singleton lazy loader
_lazy_loader = LazyServiceLoader()

# Expose commonly used services for direct import
def __getattr__(name: str) -> Type:
    """Module-level lazy loading."""
    return getattr(_lazy_loader, name)


# Export all service names for IDEs and static analysis
__all__ = [
    "BaseService",
    "ServiceRegistry", 
    "ServiceManager",
    "UserService",
    "WalletService", 
    "VendorService",
    "ProductService",
    "OrderService",
    "DisputeService",
    "MessagingService",
    "SupportService",
    "get_service",
    "preload_services",
]


def get_service(service_name: str, **kwargs) -> Optional[Any]:
    """
    Get an instance of a service with lazy loading.
    
    Args:
        service_name: Name of the service to get
        **kwargs: Configuration parameters for the service
    
    Returns:
        Service instance or None if not found
    """
    try:
        service_class = getattr(_lazy_loader, service_name)
        return service_class.get_instance(**kwargs)
    except AttributeError:
        return None


def preload_services(service_names: list = None) -> None:
    """
    Preload specific services or all services.
    
    Args:
        service_names: List of service names to preload. If None, preloads all.
    """
    if service_names is None:
        _lazy_loader.preload_all()
    else:
        for service_name in service_names:
            _lazy_loader.preload_service(service_name)


# Preload only critical services by default
def _preload_critical_services():
    """Preload only the most commonly used services."""
    critical_services = ['BaseService', 'ServiceRegistry', 'ServiceManager']
    for service in critical_services:
        try:
            _lazy_loader.preload_service(service)
        except Exception:
            pass  # Ignore errors during preloading


# Initialize critical services
_preload_critical_services()
