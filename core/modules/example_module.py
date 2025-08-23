"""
Example Module
Demonstrates how to create a simple module using the modular system.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from django.http import HttpResponse
from django.views import View

from ..architecture.base import BaseModule
from ..architecture.decorators import dependency, module, provides_models, provides_views
from ..architecture.interfaces import ModelInterface, ViewInterface

logger = logging.getLogger(__name__)


class ExampleView(View):
    """Example view provided by the example module."""

    def get(self, request):
        """Handle GET request."""
        return HttpResponse("Hello from Example Module!")


@module(
    name="example",
    version="1.0.0",
    description="Example module demonstrating the modular system",
    author="Marketplace Team",
    dependencies=[],
    required_settings=[],
)
@provides_models()  # No models provided
@provides_views(example_view="core.modules.example_module.ExampleView")
class ExampleModule(BaseModule, ModelInterface, ViewInterface):
    """
    Example module that demonstrates the modular system capabilities.
    """

    def __init__(self, **kwargs):
        """Initialize the example module."""
        super().__init__(**kwargs)
        self._counter = 0
        self._data = {}

    def initialize(self) -> bool:
        """Initialize the example module."""
        try:
            # Set up any resources, connections, etc.
            self._counter = 0
            self._data = {}

            # Log initialization
            logger.info(f"Example module {self.name} initialized successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize example module: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the example module."""
        try:
            # Clean up resources
            self._counter = 0
            self._data.clear()

            logger.info(f"Example module {self.name} cleaned up successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup example module: {e}")
            return False

    def get_models(self) -> List[Type]:
        """Get models provided by this module."""
        return []

    def get_admin_models(self) -> Dict[str, Type]:
        """Get admin models for this module."""
        return {}

    def get_signals(self) -> List:
        """Get signals provided by this module."""
        return []

    def get_urls(self) -> List:
        """Get URL patterns for this module."""
        from django.urls import path

        return [
            path("example/", ExampleView.as_view(), name="example_view"),
        ]

    def get_views(self) -> Dict[str, Type[View]]:
        """Get views provided by this module."""
        return {
            "example_view": ExampleView,
        }

    def get_permissions(self) -> Dict[str, List[str]]:
        """Get permissions required by this module."""
        return {
            "example_view": ["core.view_example"],
        }

    # Module-specific functionality
    def increment_counter(self) -> int:
        """Increment the internal counter."""
        self._counter += 1
        logger.info(f"Counter incremented to {self._counter}")
        return self._counter

    def get_counter(self) -> int:
        """Get the current counter value."""
        return self._counter

    def set_data(self, key: str, value: Any) -> None:
        """Set data in the module."""
        self._data[key] = value
        logger.info(f"Data set: {key} = {value}")

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from the module."""
        return self._data.get(key, default)

    def get_all_data(self) -> Dict[str, Any]:
        """Get all data from the module."""
        return self._data.copy()

    def clear_data(self) -> None:
        """Clear all data from the module."""
        self._data.clear()
        logger.info("All data cleared")

    def get_module_health(self) -> Dict[str, Any]:
        """Get health status of this module."""
        return {
            "module_name": self.name,
            "version": self.version,
            "enabled": self.is_enabled(),
            "counter_value": self._counter,
            "data_count": len(self._data),
            "last_operation": getattr(self, "_last_operation", "none"),
        }

    def get_module_metrics(self) -> Dict[str, Any]:
        """Get metrics for this module."""
        return {
            "counter_increments": getattr(self, "_counter_increments", 0),
            "data_operations": getattr(self, "_data_operations", 0),
            "view_requests": getattr(self, "_view_requests", 0),
        }

    def validate_configuration(self) -> bool:
        """Validate module configuration."""
        try:
            # Check if counter is valid
            if self._counter < 0:
                logger.error("Counter cannot be negative")
                return False

            # Check if data is accessible
            if not isinstance(self._data, dict):
                logger.error("Data storage must be a dictionary")
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this module."""
        return {
            "max_counter_value": {
                "type": "integer",
                "description": "Maximum value for the counter",
                "default": 1000,
                "required": False,
            },
            "data_retention_days": {
                "type": "integer",
                "description": "Number of days to retain data",
                "default": 30,
                "required": False,
            },
            "enable_logging": {
                "type": "boolean",
                "description": "Enable detailed logging",
                "default": True,
                "required": False,
            },
        }

    def set_configuration(self, config: Dict[str, Any]) -> bool:
        """Set module configuration."""
        try:
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")

            logger.info(f"Configuration updated for module {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update configuration for module {self.name}: {e}")
            return False

    def perform_health_check(self) -> bool:
        """Perform a custom health check."""
        try:
            # Check if counter is reasonable
            if self._counter > 1000000:
                logger.warning("Counter value is very high")
                return False

            # Check if data storage is working
            test_key = "_health_check_test"
            test_value = "test_value"

            self.set_data(test_key, test_value)
            retrieved_value = self.get_data(test_key)

            if retrieved_value != test_value:
                logger.error("Data storage health check failed")
                return False

            # Clean up test data
            del self._data[test_key]

            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_module_info(self) -> Dict[str, Any]:
        """Get comprehensive module information."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.is_enabled(),
            "dependencies": self.get_dependencies(),
            "health": self.get_module_health(),
            "metrics": self.get_module_metrics(),
            "configuration": self.get_configuration_schema(),
            "capabilities": {
                "models": len(self.get_models()),
                "views": len(self.get_views()),
                "signals": len(self.get_signals()),
                "urls": len(self.get_urls()),
            },
        }
