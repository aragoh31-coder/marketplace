"""
Service Registry
Manages registration and discovery of services in the system.
"""

from typing import Dict, List, Any, Optional, Type, Set
from .base_service import BaseService
from ..architecture.exceptions import ServiceNotFoundError, ServiceError
import logging

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Registry for managing all services in the system.
    """
    
    _services: Dict[str, BaseService] = {}
    _service_classes: Dict[str, Type[BaseService]] = {}
    _service_groups: Dict[str, Set[str]] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, service_class: Type[BaseService]) -> None:
        """Register a service class."""
        if not issubclass(service_class, BaseService):
            raise TypeError(f"{service_class} must inherit from BaseService")
        
        service_name = service_class.service_name
        if not service_name:
            raise ValueError(f"Service class {service_class} must have a service_name")
        
        cls._service_classes[service_name] = service_class
        logger.info(f"Registered service class: {service_name}")
    
    @classmethod
    def create_service(cls, service_name: str, **kwargs) -> Optional[BaseService]:
        """Create and register a service instance."""
        if service_name not in cls._service_classes:
            logger.error(f"Unknown service: {service_name}")
            return None
        
        try:
            service_class = cls._service_classes[service_name]
            service_instance = service_class(**kwargs)
            cls._services[service_name] = service_instance
            logger.info(f"Created service instance: {service_name}")
            return service_instance
        except Exception as e:
            logger.error(f"Failed to create service {service_name}: {e}")
            return None
    
    @classmethod
    def get_service(cls, service_name: str) -> Optional[BaseService]:
        """Get a service instance by name."""
        return cls._services.get(service_name)
    
    @classmethod
    def has_service(cls, service_name: str) -> bool:
        """Check if a service exists."""
        return service_name in cls._services
    
    @classmethod
    def get_all_services(cls) -> Dict[str, BaseService]:
        """Get all registered services."""
        return cls._services.copy()
    
    @classmethod
    def get_available_services(cls) -> Dict[str, BaseService]:
        """Get all available services."""
        return {name: service for name, service in cls._services.items() 
                if service.is_available()}
    
    @classmethod
    def get_healthy_services(cls) -> Dict[str, BaseService]:
        """Get all healthy services."""
        return {name: service for name, service in cls._services.items() 
                if service.get_health_status()['healthy']}
    
    @classmethod
    def get_service_by_type(cls, service_type: Type[BaseService]) -> List[BaseService]:
        """Get all services of a specific type."""
        return [service for service in cls._services.values() 
                if isinstance(service, service_type)]
    
    @classmethod
    def group_service(cls, service_name: str, group_name: str) -> None:
        """Add a service to a group."""
        if group_name not in cls._service_groups:
            cls._service_groups[group_name] = set()
        
        cls._service_groups[group_name].add(service_name)
        logger.info(f"Added service {service_name} to group {group_name}")
    
    @classmethod
    def get_services_in_group(cls, group_name: str) -> List[BaseService]:
        """Get all services in a specific group."""
        if group_name not in cls._service_groups:
            return []
        
        services = []
        for service_name in cls._service_groups[group_name]:
            service = cls._services.get(service_name)
            if service:
                services.append(service)
        
        return services
    
    @classmethod
    def get_service_groups(cls) -> Dict[str, Set[str]]:
        """Get all service groups."""
        return cls._service_groups.copy()
    
    @classmethod
    def initialize_all(cls) -> bool:
        """Initialize all registered services."""
        if cls._initialized:
            return True
        
        success = True
        
        for service_name, service in cls._services.items():
            if not service.is_available():
                try:
                    if service.initialize():
                        logger.info(f"Service {service_name} initialized successfully")
                    else:
                        logger.error(f"Service {service_name} failed to initialize")
                        success = False
                except Exception as e:
                    logger.error(f"Service {service_name} initialization error: {e}")
                    success = False
        
        cls._initialized = success
        return success
    
    @classmethod
    def cleanup_all(cls) -> bool:
        """Clean up all services."""
        success = True
        
        for service_name, service in cls._services.items():
            try:
                if not service.cleanup():
                    logger.error(f"Service {service_name} failed to cleanup")
                    success = False
            except Exception as e:
                logger.error(f"Service {service_name} cleanup error: {e}")
                success = False
        
        cls._initialized = False
        return success
    
    @classmethod
    def reload_service(cls, service_name: str) -> bool:
        """Reload a specific service."""
        service = cls._services.get(service_name)
        if not service:
            return False
        
        try:
            # Cleanup and reinitialize
            if not service.cleanup():
                return False
            
            return service.initialize()
        except Exception as e:
            logger.error(f"Failed to reload service {service_name}: {e}")
            return False
    
    @classmethod
    def get_service_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all services."""
        info = {}
        for name, service in cls._services.items():
            info[name] = {
                'service_name': service.service_name,
                'version': service.version,
                'description': service.description,
                'author': service.author,
                'available': service.is_available(),
                'healthy': service.get_health_status()['healthy'],
                'config_keys': list(service.config.keys()),
                'cache_enabled': service.cache_timeout > 0,
                'retry_attempts': service.retry_attempts,
                'retry_delay': service.retry_delay
            }
        return info
    
    @classmethod
    def get_service_health_summary(cls) -> Dict[str, Any]:
        """Get a summary of all service health statuses."""
        total_services = len(cls._services)
        available_services = len(cls.get_available_services())
        healthy_services = len(cls.get_healthy_services())
        
        return {
            'total_services': total_services,
            'available_services': available_services,
            'healthy_services': healthy_services,
            'unavailable_services': total_services - available_services,
            'unhealthy_services': available_services - healthy_services,
            'overall_health': healthy_services / total_services if total_services > 0 else 0
        }
    
    @classmethod
    def get_service_metrics(cls) -> Dict[str, Dict[str, Any]]:
        """Get metrics from all services."""
        metrics = {}
        for name, service in cls._services.items():
            try:
                metrics[name] = service.get_metrics()
            except Exception as e:
                logger.error(f"Failed to get metrics for service {name}: {e}")
                metrics[name] = {'error': str(e)}
        
        return metrics
    
    @classmethod
    def validate_service_dependencies(cls) -> Dict[str, List[str]]:
        """Validate service dependencies and return any issues."""
        issues = {}
        
        for service_name, service in cls._services.items():
            service_issues = []
            
            # Check if service is available
            if not service.is_available():
                service_issues.append("Service not available")
            
            # Check if service is healthy
            if not service.get_health_status()['healthy']:
                service_issues.append("Service unhealthy")
            
            # Check configuration
            required_config = service.get_required_config()
            for config_key in required_config:
                if config_key not in service.config:
                    service_issues.append(f"Missing required config: {config_key}")
            
            if service_issues:
                issues[service_name] = service_issues
        
        return issues
    
    @classmethod
    def get_service_dependencies(cls) -> Dict[str, List[str]]:
        """Get dependency information for all services."""
        dependencies = {}
        
        for service_name, service in cls._services.items():
            # This is a simple implementation - in a real system you might
            # want to track actual service dependencies
            dependencies[service_name] = []
        
        return dependencies
    
    @classmethod
    def shutdown(cls) -> None:
        """Shutdown the service registry and all services."""
        logger.info("Shutting down service registry...")
        
        # Cleanup all services
        cls.cleanup_all()
        
        # Clear registries
        cls._services.clear()
        cls._service_classes.clear()
        cls._service_groups.clear()
        cls._initialized = False
        
        logger.info("Service registry shutdown complete")