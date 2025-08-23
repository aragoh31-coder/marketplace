"""
Design System Module
Modular implementation of the design system functionality.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from ..architecture.base import BaseModule
from ..architecture.decorators import module, provides_models, provides_templates, provides_views
from ..architecture.interfaces import ModelInterface, TemplateInterface, ViewInterface
from ..design_system import DesignSystem

logger = logging.getLogger(__name__)


@module(
    name="design_system",
    version="2.0.0",
    description="Modular design system for consistent application theming",
    author="Marketplace Team",
    dependencies=[],
    required_settings=["STATIC_URL", "STATICFILES_DIRS"],
)
@provides_templates("templates/design_system")
@provides_views(design_system_admin="core.admin.DesignSystemAdmin", theme_preview="core.views.ThemePreviewView")
class DesignSystemModule(BaseModule, ModelInterface, ViewInterface, TemplateInterface):
    """
    Modular design system that provides theming capabilities.
    """

    def __init__(self, **kwargs):
        """Initialize the design system module."""
        super().__init__(**kwargs)
        self.design_system = DesignSystem()
        self._theme_cache = {}

    def initialize(self) -> bool:
        """Initialize the design system module."""
        try:
            # Initialize the design system
            self.design_system.load_theme()

            # Register template tags
            self._register_template_tags()

            # Set up signal handlers
            self._setup_signals()

            logger.info(f"Design system module {self.name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize design system module: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the design system module."""
        try:
            # Clear theme cache
            self._theme_cache.clear()

            # Clean up signal handlers
            self._cleanup_signals()

            logger.info(f"Design system module {self.name} cleaned up successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup design system module: {e}")
            return False

    def _register_template_tags(self):
        """Register template tags for the design system."""
        # Template tags are automatically loaded by Django
        # This method can be used for custom registration if needed
        pass

    def _setup_signals(self):
        """Set up signal handlers for the design system."""
        # Set up signals for theme changes, etc.
        pass

    def _cleanup_signals(self):
        """Clean up signal handlers."""
        # Disconnect signals
        pass

    def get_models(self) -> List[Type]:
        """Get models provided by this module."""
        # The design system module doesn't provide models directly
        # but it can be extended to do so
        return []

    def get_admin_models(self) -> Dict[str, Type]:
        """Get admin models for this module."""
        from ..admin import DesignSystemAdmin

        return {"design_system": DesignSystemAdmin}

    def get_signals(self) -> List:
        """Get signals provided by this module."""
        return []

    def get_urls(self) -> List:
        """Get URL patterns for this module."""
        from django.urls import path

        from ..views import ThemePreviewView

        return [
            path("design-system/", ThemePreviewView.as_view(), name="design_system_preview"),
            path(
                "design-system/admin/", self.get_admin_models()["design_system"].as_view(), name="design_system_admin"
            ),
        ]

    def get_views(self) -> Dict[str, Type]:
        """Get views provided by this module."""
        from ..admin import DesignSystemAdmin
        from ..views import ThemePreviewView

        return {
            "theme_preview": ThemePreviewView,
            "design_system_admin": DesignSystemAdmin,
        }

    def get_permissions(self) -> Dict[str, List[str]]:
        """Get permissions required by this module."""
        return {
            "design_system_admin": ["core.change_design_system"],
            "theme_preview": ["core.view_design_system"],
        }

    def get_template_dirs(self) -> List[str]:
        """Get template directories for this module."""
        return ["templates/design_system"]

    def get_context_processors(self) -> List[str]:
        """Get context processors for this module."""
        return []

    def get_template_tags(self) -> List[str]:
        """Get template tags for this module."""
        return ["core.templatetags.design_system"]

    def get_theme_info(self) -> Dict[str, Any]:
        """Get information about the current theme."""
        return self.design_system.get_theme_info()

    def update_theme(self, theme_data: Dict[str, Any]) -> bool:
        """Update the current theme."""
        try:
            success = self.design_system.update_theme(theme_data)
            if success:
                # Clear theme cache
                self._theme_cache.clear()
                logger.info(f"Theme updated successfully in module {self.name}")
            return success
        except Exception as e:
            logger.error(f"Failed to update theme in module {self.name}: {e}")
            return False

    def get_theme_colors(self) -> Dict[str, str]:
        """Get all theme colors."""
        cache_key = "theme_colors"
        if cache_key not in self._theme_cache:
            self._theme_cache[cache_key] = self.design_system.theme["colors"]
        return self._theme_cache[cache_key]

    def get_theme_spacing(self) -> Dict[str, str]:
        """Get all theme spacing values."""
        cache_key = "theme_spacing"
        if cache_key not in self._theme_cache:
            self._theme_cache[cache_key] = self.design_system.theme["spacing"]
        return self._theme_cache[cache_key]

    def get_theme_typography(self) -> Dict[str, str]:
        """Get all theme typography values."""
        cache_key = "theme_typography"
        if cache_key not in self._theme_cache:
            self._theme_cache[cache_key] = self.design_system.theme["typography"]
        return self._theme_cache[cache_key]

    def generate_css_variables(self) -> str:
        """Generate CSS variables string."""
        return self.design_system.generate_css_variables()

    def export_theme(self) -> Dict[str, Any]:
        """Export the current theme configuration."""
        return self.design_system.theme.copy()

    def import_theme(self, theme_data: Dict[str, Any]) -> bool:
        """Import a theme configuration."""
        return self.update_theme(theme_data)

    def reset_theme(self) -> bool:
        """Reset to default theme."""
        try:
            success = self.design_system.reset_to_default()
            if success:
                # Clear theme cache
                self._theme_cache.clear()
                logger.info(f"Theme reset to default in module {self.name}")
            return success
        except Exception as e:
            logger.error(f"Failed to reset theme in module {self.name}: {e}")
            return False

    def get_module_health(self) -> Dict[str, Any]:
        """Get health status of this module."""
        return {
            "module_name": self.name,
            "version": self.version,
            "enabled": self.is_enabled(),
            "theme_loaded": hasattr(self.design_system, "theme"),
            "cache_size": len(self._theme_cache),
            "last_theme_update": getattr(self.design_system, "_last_update", None),
        }

    def get_module_metrics(self) -> Dict[str, Any]:
        """Get metrics for this module."""
        return {
            "theme_changes": getattr(self.design_system, "_theme_changes", 0),
            "cache_hits": getattr(self.design_system, "_cache_hits", 0),
            "cache_misses": getattr(self.design_system, "_cache_misses", 0),
            "css_generations": getattr(self.design_system, "_css_generations", 0),
        }

    def validate_configuration(self) -> bool:
        """Validate module configuration."""
        try:
            # Check if design system can load theme
            theme_info = self.design_system.get_theme_info()
            if not theme_info:
                return False

            # Check if required theme components exist
            required_components = ["colors", "typography", "spacing"]
            for component in required_components:
                if component not in self.design_system.theme:
                    logger.error(f"Missing required theme component: {component}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this module."""
        return {
            "theme_file_path": {
                "type": "string",
                "description": "Path to custom theme JSON file",
                "default": "core/themes/custom_theme.json",
                "required": False,
            },
            "cache_timeout": {
                "type": "integer",
                "description": "Theme cache timeout in seconds",
                "default": 3600,
                "required": False,
            },
            "auto_reload": {
                "type": "boolean",
                "description": "Automatically reload theme on file changes",
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
