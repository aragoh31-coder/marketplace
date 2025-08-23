"""
Base Module System
Provides the foundation for creating modular Django applications.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)


class BaseModule(ABC):
    """
    Base class for all modules in the system.
    Modules are self-contained units of functionality.
    """
    
    # Module metadata
    name: str = None
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = []
    required_settings: List[str] = []
    
    # Module state
    _initialized: bool = False
    _enabled: bool = True
    _config: Dict[str, Any] = {}
    
    def __init__(self, **kwargs):
        """Initialize the module with configuration."""
        self._config = kwargs
        self._initialized = False
        self._enabled = True
        
        # Validate module configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate module configuration."""
        if not self.name:
            raise ImproperlyConfigured(f"Module {self.__class__.__name__} must have a name")
        
        # Check required settings
        for setting in self.required_settings:
            if not hasattr(settings, setting):
                logger.warning(f"Module {self.name} requires setting: {setting}")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the module. This is where you set up models, 
        register signals, etc.
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """
        Clean up the module. This is where you clean up resources,
        unregister signals, etc.
        """
        pass
    
    def enable(self) -> bool:
        """Enable the module."""
        if not self._initialized:
            if not self.initialize():
                return False
        self._enabled = True
        logger.info(f"Module {self.name} enabled")
        return True
    
    def disable(self) -> bool:
        """Disable the module."""
        if self._enabled:
            if not self.cleanup():
                return False
        self._enabled = False
        logger.info(f"Module {self.name} disabled")
        return True
    
    def is_enabled(self) -> bool:
        """Check if the module is enabled."""
        return self._enabled and self._initialized
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get module configuration value."""
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set module configuration value."""
        self._config[key] = value
    
    def get_dependencies(self) -> List[str]:
        """Get list of module dependencies."""
        return self.dependencies.copy()
    
    def check_dependencies(self) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in self.dependencies:
            if not ModuleRegistry.has_module(dep):
                logger.error(f"Module {self.name} missing dependency: {dep}")
                return False
        return True
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"


class ModuleRegistry:
    """
    Registry for managing all modules in the system.
    """
    
    _modules: Dict[str, BaseModule] = {}
    _module_classes: Dict[str, Type[BaseModule]] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, module_class: Type[BaseModule]) -> None:
        """Register a module class."""
        if not issubclass(module_class, BaseModule):
            raise TypeError(f"{module_class} must inherit from BaseModule")
        
        module_name = module_class.name
        if not module_name:
            raise ValueError(f"Module class {module_class} must have a name")
        
        cls._module_classes[module_name] = module_class
        logger.info(f"Registered module class: {module_name}")
    
    @classmethod
    def create_module(cls, module_name: str, **kwargs) -> Optional[BaseModule]:
        """Create and register a module instance."""
        if module_name not in cls._module_classes:
            logger.error(f"Unknown module: {module_name}")
            return None
        
        try:
            module_class = cls._module_classes[module_name]
            module_instance = module_class(**kwargs)
            cls._modules[module_name] = module_instance
            logger.info(f"Created module instance: {module_name}")
            return module_instance
        except Exception as e:
            logger.error(f"Failed to create module {module_name}: {e}")
            return None
    
    @classmethod
    def get_module(cls, module_name: str) -> Optional[BaseModule]:
        """Get a module instance by name."""
        return cls._modules.get(module_name)
    
    @classmethod
    def has_module(cls, module_name: str) -> bool:
        """Check if a module exists."""
        return module_name in cls._modules
    
    @classmethod
    def get_all_modules(cls) -> Dict[str, BaseModule]:
        """Get all registered modules."""
        return cls._modules.copy()
    
    @classmethod
    def get_enabled_modules(cls) -> Dict[str, BaseModule]:
        """Get all enabled modules."""
        return {name: module for name, module in cls._modules.items() 
                if module.is_enabled()}
    
    @classmethod
    def initialize_all(cls) -> bool:
        """Initialize all registered modules."""
        if cls._initialized:
            return True
        
        # Sort modules by dependencies
        sorted_modules = cls._sort_by_dependencies()
        
        for module_name in sorted_modules:
            module = cls._modules.get(module_name)
            if module and not module.is_enabled():
                if not module.enable():
                    logger.error(f"Failed to initialize module: {module_name}")
                    return False
        
        cls._initialized = True
        logger.info("All modules initialized successfully")
        return True
    
    @classmethod
    def cleanup_all(cls) -> bool:
        """Clean up all modules."""
        success = True
        
        for module_name, module in cls._modules.items():
            if module.is_enabled():
                if not module.disable():
                    logger.error(f"Failed to cleanup module: {module_name}")
                    success = False
        
        cls._initialized = False
        return success
    
    @classmethod
    def _sort_by_dependencies(cls) -> List[str]:
        """Sort modules by dependency order using topological sort."""
        # Build dependency graph
        graph = {}
        in_degree = {}
        
        for module_name in cls._modules:
            graph[module_name] = []
            in_degree[module_name] = 0
        
        for module_name, module in cls._modules.items():
            for dep in module.get_dependencies():
                if dep in cls._modules:
                    graph[dep].append(module_name)
                    in_degree[module_name] += 1
        
        # Topological sort
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for dependent in graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(cls._modules):
            logger.warning("Circular dependency detected in modules")
            # Fallback to original order
            return list(cls._modules.keys())
        
        return result
    
    @classmethod
    def reload_module(cls, module_name: str) -> bool:
        """Reload a specific module."""
        module = cls._modules.get(module_name)
        if not module:
            return False
        
        # Disable and re-enable
        if module.is_enabled():
            if not module.disable():
                return False
        
        return module.enable()
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all modules."""
        info = {}
        for name, module in cls._modules.items():
            info[name] = {
                'name': module.name,
                'version': module.version,
                'description': module.description,
                'author': module.author,
                'enabled': module.is_enabled(),
                'dependencies': module.get_dependencies(),
                'config': module._config.copy()
            }
        return info