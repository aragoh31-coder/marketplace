"""
Decorators for Module and Service Registration
Make it easy to register modules and services with the system.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .base import BaseModule, ModuleRegistry
from .interfaces import ServiceInterface

logger = logging.getLogger(__name__)


def module(
    name: str = None,
    version: str = "1.0.0",
    description: str = "",
    author: str = "",
    dependencies: List[str] = None,
    required_settings: List[str] = None,
    auto_register: bool = True,
):
    """
    Decorator to register a class as a module.

    Args:
        name: Module name (defaults to class name)
        version: Module version
        description: Module description
        author: Module author
        dependencies: List of module dependencies
        required_settings: List of required Django settings
        auto_register: Whether to automatically register the module
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        # Set module metadata
        if name:
            cls.name = name
        elif not hasattr(cls, "name") or not cls.name:
            cls.name = cls.__name__

        cls.version = version
        cls.description = description
        cls.author = author

        if dependencies:
            cls.dependencies = dependencies
        if required_settings:
            cls.required_settings = required_settings

        # Auto-register if requested
        if auto_register:
            ModuleRegistry.register(cls)
            logger.info(f"Auto-registered module: {cls.name}")

        return cls

    return decorator


def service(service_name: str = None, auto_register: bool = True):
    """
    Decorator to register a class as a service.

    Args:
        service_name: Service name (defaults to class name)
        auto_register: Whether to automatically register the service
    """

    def decorator(cls: Type[ServiceInterface]) -> Type[ServiceInterface]:
        # Set service metadata
        if service_name:
            cls.service_name = service_name
        elif not hasattr(cls, "service_name") or not cls.service_name:
            cls.service_name = cls.__name__

        # Auto-register if requested
        if auto_register:
            # Register with service registry (to be implemented)
            logger.info(f"Auto-registered service: {cls.service_name}")

        return cls

    return decorator


def dependency(module_name: str, required: bool = True, version: str = None):
    """
    Decorator to declare module dependencies.

    Args:
        module_name: Name of the required module
        required: Whether the dependency is required
        version: Required version of the dependency
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "dependencies"):
            cls.dependencies = []

        if not hasattr(cls, "optional_dependencies"):
            cls.optional_dependencies = []

        if required:
            if module_name not in cls.dependencies:
                cls.dependencies.append(module_name)
        else:
            if module_name not in cls.optional_dependencies:
                cls.optional_dependencies.append(module_name)

        return cls

    return decorator


def requires_setting(setting_name: str, default_value: Any = None):
    """
    Decorator to declare required Django settings.

    Args:
        setting_name: Name of the required setting
        default_value: Default value if setting is missing
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "required_settings"):
            cls.required_settings = []

        if not hasattr(cls, "default_settings"):
            cls.default_settings = {}

        cls.required_settings.append(setting_name)
        if default_value is not None:
            cls.default_settings[setting_name] = default_value

        return cls

    return decorator


def provides_models(*model_classes: Type):
    """
    Decorator to declare models provided by a module.

    Args:
        *model_classes: Model classes provided by the module
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "provided_models"):
            cls.provided_models = []

        cls.provided_models.extend(model_classes)
        return cls

    return decorator


def provides_views(**view_mapping: Dict[str, Type]):
    """
    Decorator to declare views provided by a module.

    Args:
        **view_mapping: Mapping of view names to view classes
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "provided_views"):
            cls.provided_views = {}

        cls.provided_views.update(view_mapping)
        return cls

    return decorator


def provides_tasks(*task_names: str):
    """
    Decorator to declare tasks provided by a module.

    Args:
        *task_names: Names of tasks provided by the module
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "provided_tasks"):
            cls.provided_tasks = []

        cls.provided_tasks.extend(task_names)
        return cls

    return decorator


def provides_api_endpoints(*endpoints: str):
    """
    Decorator to declare API endpoints provided by a module.

    Args:
        *endpoints: API endpoint paths provided by the module
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "provided_api_endpoints"):
            cls.provided_api_endpoints = []

        cls.provided_api_endpoints.extend(endpoints)
        return cls

    return decorator


def provides_middleware(middleware_class: str, order: int = 100):
    """
    Decorator to declare middleware provided by a module.

    Args:
        middleware_class: Middleware class path
        order: Execution order (lower numbers execute first)
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "provided_middleware"):
            cls.provided_middleware = {}

        cls.provided_middleware[middleware_class] = order
        return cls

    return decorator


def provides_templates(*template_dirs: str):
    """
    Decorator to declare template directories provided by a module.

    Args:
        *template_dirs: Template directory paths
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "provided_template_dirs"):
            cls.provided_template_dirs = []

        cls.provided_template_dirs.extend(template_dirs)
        return cls

    return decorator


def provides_static_files(*static_dirs: str):
    """
    Decorator to declare static file directories provided by a module.

    Args:
        *static_dirs: Static file directory paths
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "provided_static_dirs"):
            cls.provided_static_dirs = []

        cls.provided_static_dirs.extend(static_dirs)
        return cls

    return decorator


def configurable(*config_keys: str):
    """
    Decorator to declare configurable options for a module.

    Args:
        *config_keys: Configuration option keys
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "configurable_options"):
            cls.configurable_options = []

        cls.configurable_options.extend(config_keys)
        return cls

    return decorator


def lifecycle_hook(hook_name: str):
    """
    Decorator to mark methods as lifecycle hooks.

    Args:
        hook_name: Name of the lifecycle hook
    """

    def decorator(method: Callable) -> Callable:
        if not hasattr(method, "_lifecycle_hooks"):
            method._lifecycle_hooks = []

        method._lifecycle_hooks.append(hook_name)

        @wraps(method)
        def wrapper(*args, **kwargs):
            return method(*args, **kwargs)

        # Copy the lifecycle hooks to the wrapper
        wrapper._lifecycle_hooks = method._lifecycle_hooks

        return wrapper

    return decorator


def validate_config(validation_func: Callable):
    """
    Decorator to add custom configuration validation.

    Args:
        validation_func: Function that validates configuration
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not hasattr(cls, "_custom_validators"):
            cls._custom_validators = []

        cls._custom_validators.append(validation_func)
        return cls

    return decorator


def auto_discover(discovery_path: str = None):
    """
    Decorator to enable auto-discovery for a module.

    Args:
        discovery_path: Path to search for related files
    """

    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        cls.auto_discover = True
        if discovery_path:
            cls.discovery_path = discovery_path
        return cls

    return decorator
