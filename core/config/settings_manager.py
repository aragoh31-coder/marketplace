"""
Settings Manager
Manages Django settings in a modular way.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages Django settings in a modular and organized way.
    """

    def __init__(self):
        """Initialize the settings manager."""
        self._module_settings: Dict[str, Dict[str, Any]] = {}
        self._default_settings: Dict[str, Any] = {}
        self._environment_overrides: Dict[str, Any] = {}
        self._validation_rules: Dict[str, Dict[str, Any]] = {}

        # Load default settings
        self._load_default_settings()

        # Load environment overrides
        self._load_environment_overrides()

    def _load_default_settings(self):
        """Load default settings for all modules."""
        self._default_settings = {
            # Core settings
            "DEBUG": False,
            "SECRET_KEY": "",
            "ALLOWED_HOSTS": ["localhost", "127.0.0.1"],
            # Database settings
            "DATABASES": {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": "db.sqlite3",
                }
            },
            # Cache settings
            "CACHES": {
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                }
            },
            # Static files
            "STATIC_URL": "/static/",
            "STATIC_ROOT": "staticfiles",
            "STATICFILES_DIRS": ["static"],
            # Media files
            "MEDIA_URL": "/media/",
            "MEDIA_ROOT": "media",
            # Templates
            "TEMPLATES": [
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": ["templates"],
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.debug",
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                },
            ],
            # Middleware
            "MIDDLEWARE": [
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
                "django.middleware.clickjacking.XFrameOptionsMiddleware",
            ],
            # Installed apps
            "INSTALLED_APPS": [
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
            ],
            # Security settings
            "SECURE_BROWSER_XSS_FILTER": True,
            "SECURE_CONTENT_TYPE_NOSNIFF": True,
            "X_FRAME_OPTIONS": "DENY",
            # Logging
            "LOGGING": {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "verbose": {
                        "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                        "style": "{",
                    },
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "verbose",
                    },
                },
                "root": {
                    "handlers": ["console"],
                    "level": "INFO",
                },
            },
        }

    def _load_environment_overrides(self):
        """Load environment variable overrides."""
        # Load from .env file if it exists
        env_file = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            self._environment_overrides[key] = value
            except Exception as e:
                logger.warning(f"Failed to load .env file: {e}")

        # Load from environment variables
        for key, value in os.environ.items():
            if key.startswith("DJANGO_"):
                # Convert DJANGO_DEBUG to DEBUG
                django_key = key.replace("DJANGO_", "")
                self._environment_overrides[django_key] = value

    def register_module_settings(self, module_name: str, settings_dict: Dict[str, Any]):
        """Register settings for a specific module."""
        self._module_settings[module_name] = settings_dict.copy()
        logger.info(f"Registered settings for module: {module_name}")

    def get_module_settings(self, module_name: str) -> Dict[str, Any]:
        """Get settings for a specific module."""
        return self._module_settings.get(module_name, {}).copy()

    def get_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get a setting value with fallback to default."""
        # Check environment overrides first
        if setting_name in self._environment_overrides:
            return self._environment_overrides[setting_name]

        # Check Django settings
        if hasattr(settings, setting_name):
            return getattr(settings, setting_name)

        # Check module settings
        for module_settings in self._module_settings.values():
            if setting_name in module_settings:
                return module_settings[setting_name]

        # Check default settings
        if setting_name in self._default_settings:
            return self._default_settings[setting_name]

        return default

    def set_setting(self, setting_name: str, value: Any, module_name: str = None):
        """Set a setting value."""
        if module_name:
            if module_name not in self._module_settings:
                self._module_settings[module_name] = {}
            self._module_settings[module_name][setting_name] = value
            logger.info(f"Set setting {setting_name} for module {module_name}")
        else:
            # Set in Django settings (if possible)
            if hasattr(settings, setting_name):
                setattr(settings, setting_name, value)
                logger.info(f"Set Django setting: {setting_name}")
            else:
                # Store in default settings
                self._default_settings[setting_name] = value
                logger.info(f"Set default setting: {setting_name}")

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings from all sources."""
        all_settings = {}

        # Start with default settings
        all_settings.update(self._default_settings)

        # Add module settings
        for module_name, module_settings in self._module_settings.items():
            for key, value in module_settings.items():
                all_settings[f"{module_name}.{key}"] = value

        # Add Django settings
        for key in dir(settings):
            if key.isupper() and not key.startswith("_"):
                try:
                    value = getattr(settings, key)
                    all_settings[key] = value
                except Exception:
                    pass

        # Override with environment variables
        all_settings.update(self._environment_overrides)

        return all_settings

    def validate_settings(self) -> Dict[str, List[str]]:
        """Validate all settings and return any issues."""
        issues = {}

        # Validate required settings
        required_settings = [
            "SECRET_KEY",
            "DATABASES",
            "INSTALLED_APPS",
        ]

        for setting_name in required_settings:
            if not self.get_setting(setting_name):
                if "core" not in issues:
                    issues["core"] = []
                issues["core"].append(f"Missing required setting: {setting_name}")

        # Validate module-specific settings
        for module_name, module_settings in self._module_settings.items():
            module_issues = []

            # Check for validation rules
            if module_name in self._validation_rules:
                rules = self._validation_rules[module_name]
                for setting_name, rule in rules.items():
                    if setting_name in module_settings:
                        value = module_settings[setting_name]
                        if not self._validate_setting_value(value, rule):
                            module_issues.append(f"Invalid value for {setting_name}: {value}")

            if module_issues:
                issues[module_name] = module_issues

        return issues

    def _validate_setting_value(self, value: Any, rule: Dict[str, Any]) -> bool:
        """Validate a setting value against a rule."""
        # Check type
        if "type" in rule:
            expected_type = rule["type"]
            if expected_type == "string" and not isinstance(value, str):
                return False
            elif expected_type == "integer" and not isinstance(value, int):
                return False
            elif expected_type == "boolean" and not isinstance(value, bool):
                return False
            elif expected_type == "list" and not isinstance(value, list):
                return False
            elif expected_type == "dict" and not isinstance(value, dict):
                return False

        # Check required
        if rule.get("required", False) and value is None:
            return False

        # Check min/max for numbers
        if isinstance(value, (int, float)):
            if "min" in rule and value < rule["min"]:
                return False
            if "max" in rule and value > rule["max"]:
                return False

        # Check length for strings/lists
        if hasattr(value, "__len__"):
            if "min_length" in rule and len(value) < rule["min_length"]:
                return False
            if "max_length" in rule and len(value) > rule["max_length"]:
                return False

        # Check allowed values
        if "allowed_values" in rule and value not in rule["allowed_values"]:
            return False

        return True

    def add_validation_rule(self, module_name: str, setting_name: str, rule: Dict[str, Any]):
        """Add a validation rule for a setting."""
        if module_name not in self._validation_rules:
            self._validation_rules[module_name] = {}

        self._validation_rules[module_name][setting_name] = rule
        logger.info(f"Added validation rule for {module_name}.{setting_name}")

    def export_settings(self, module_name: str = None) -> Dict[str, Any]:
        """Export settings to a dictionary."""
        if module_name:
            return self.get_module_settings(module_name)
        else:
            return self.get_all_settings()

    def import_settings(self, settings_dict: Dict[str, Any], module_name: str = None):
        """Import settings from a dictionary."""
        if module_name:
            self.register_module_settings(module_name, settings_dict)
        else:
            # Import all settings
            for key, value in settings_dict.items():
                if "." in key:
                    # Module setting
                    module_name, setting_name = key.split(".", 1)
                    if module_name not in self._module_settings:
                        self._module_settings[module_name] = {}
                    self._module_settings[module_name][setting_name] = value
                else:
                    # Global setting
                    self.set_setting(key, value)

    def save_settings_to_file(self, file_path: str, module_name: str = None):
        """Save settings to a JSON file."""
        try:
            settings_data = self.export_settings(module_name)

            with open(file_path, "w") as f:
                json.dump(settings_data, f, indent=2)

            logger.info(f"Settings saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save settings to {file_path}: {e}")

    def load_settings_from_file(self, file_path: str, module_name: str = None):
        """Load settings from a JSON file."""
        try:
            with open(file_path, "r") as f:
                settings_data = json.load(f)

            self.import_settings(settings_data, module_name)
            logger.info(f"Settings loaded from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load settings from {file_path}: {e}")

    def get_settings_summary(self) -> Dict[str, Any]:
        """Get a summary of all settings."""
        all_settings = self.get_all_settings()

        return {
            "total_settings": len(all_settings),
            "module_count": len(self._module_settings),
            "environment_overrides": len(self._environment_overrides),
            "validation_rules": len(self._validation_rules),
            "modules": list(self._module_settings.keys()),
            "sample_settings": dict(list(all_settings.items())[:10]),  # First 10 settings
        }


# Global settings manager instance
settings_manager = SettingsManager()
