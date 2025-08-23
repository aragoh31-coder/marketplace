"""
Module and Service Interfaces
Define contracts for modules and services in the system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from django.http import HttpRequest, HttpResponse
from django.views import View


class ModuleInterface(ABC):
    """
    Interface that all modules must implement.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the module name."""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Get the module version."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get the module description."""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if the module is enabled."""
        pass
    
    @abstractmethod
    def enable(self) -> bool:
        """Enable the module."""
        pass
    
    @abstractmethod
    def disable(self) -> bool:
        """Disable the module."""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get module configuration."""
        pass
    
    @abstractmethod
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set module configuration."""
        pass


class ServiceInterface(ABC):
    """
    Interface that all services must implement.
    """
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Get the service name."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available."""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        pass


class ViewInterface(ABC):
    """
    Interface for view-related functionality.
    """
    
    @abstractmethod
    def get_urls(self) -> List:
        """Get URL patterns for the module."""
        pass
    
    @abstractmethod
    def get_views(self) -> Dict[str, Type[View]]:
        """Get views provided by the module."""
        pass
    
    @abstractmethod
    def get_permissions(self) -> Dict[str, List[str]]:
        """Get permissions required by the module."""
        pass


class ModelInterface(ABC):
    """
    Interface for model-related functionality.
    """
    
    @abstractmethod
    def get_models(self) -> List[Type]:
        """Get models provided by the module."""
        pass
    
    @abstractmethod
    def get_admin_models(self) -> Dict[str, Type]:
        """Get admin models for the module."""
        pass
    
    @abstractmethod
    def get_signals(self) -> List:
        """Get signals provided by the module."""
        pass


class TaskInterface(ABC):
    """
    Interface for task-related functionality.
    """
    
    @abstractmethod
    def get_tasks(self) -> List[str]:
        """Get task names provided by the module."""
        pass
    
    @abstractmethod
    def get_scheduled_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get scheduled tasks for the module."""
        pass


class APIInterface(ABC):
    """
    Interface for API-related functionality.
    """
    
    @abstractmethod
    def get_api_endpoints(self) -> List[str]:
        """Get API endpoints provided by the module."""
        pass
    
    @abstractmethod
    def get_api_serializers(self) -> Dict[str, Type]:
        """Get API serializers for the module."""
        pass
    
    @abstractmethod
    def get_api_permissions(self) -> Dict[str, List[str]]:
        """Get API permissions for the module."""
        pass


class MiddlewareInterface(ABC):
    """
    Interface for middleware functionality.
    """
    
    @abstractmethod
    def get_middleware_classes(self) -> List[str]:
        """Get middleware classes for the module."""
        pass
    
    @abstractmethod
    def get_middleware_order(self) -> int:
        """Get middleware order (lower numbers execute first)."""
        pass


class TemplateInterface(ABC):
    """
    Interface for template-related functionality.
    """
    
    @abstractmethod
    def get_template_dirs(self) -> List[str]:
        """Get template directories for the module."""
        pass
    
    @abstractmethod
    def get_context_processors(self) -> List[str]:
        """Get context processors for the module."""
        pass
    
    @abstractmethod
    def get_template_tags(self) -> List[str]:
        """Get template tags for the module."""
        pass


class StaticInterface(ABC):
    """
    Interface for static file functionality.
    """
    
    @abstractmethod
    def get_static_dirs(self) -> List[str]:
        """Get static directories for the module."""
        pass
    
    @abstractmethod
    def get_static_files(self) -> List[str]:
        """Get static files for the module."""
        pass


class ConfigInterface(ABC):
    """
    Interface for configuration functionality.
    """
    
    @abstractmethod
    def get_required_settings(self) -> List[str]:
        """Get required Django settings for the module."""
        pass
    
    @abstractmethod
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default settings for the module."""
        pass
    
    @abstractmethod
    def validate_settings(self) -> bool:
        """Validate that required settings are present."""
        pass


class DependencyInterface(ABC):
    """
    Interface for dependency management.
    """
    
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Get module dependencies."""
        pass
    
    @abstractmethod
    def get_optional_dependencies(self) -> List[str]:
        """Get optional module dependencies."""
        pass
    
    @abstractmethod
    def check_dependencies(self) -> bool:
        """Check if all dependencies are satisfied."""
        pass
    
    @abstractmethod
    def get_conflicts(self) -> List[str]:
        """Get modules that conflict with this module."""
        pass