# Django Modular Architecture

A comprehensive, enterprise-grade modular architecture for Django applications that provides:

- **Modular Design**: Self-contained, pluggable modules
- **Service Layer**: Business logic and external integrations
- **Configuration Management**: Centralized, validated settings
- **Health Monitoring**: Real-time system health tracking
- **Dependency Management**: Automatic dependency resolution
- **Hot Reloading**: Module and service reloading without restarts
- **Circuit Breakers**: Fault tolerance and resilience
- **Performance Optimization**: Caching, monitoring, and metrics

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Django Application                      │
├─────────────────────────────────────────────────────────────┤
│                 Modular System Layer                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │   Modules   │ │  Services   │ │   Configuration     │  │
│  │             │ │             │ │                     │  │
│  │ • Design    │ │ • Business  │ │ • Settings          │  │
│  │ • Security  │ │ • External  │ │ • Validation        │  │
│  │ • Commerce  │ │ • Cache     │ │ • Environment       │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                 Core Architecture                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │   Registry  │ │  Interfaces │ │   Decorators        │  │
│  │             │ │             │ │                     │  │
│  │ • Module    │ │ • Contracts │ │ • @module           │  │
│  │ • Service   │ │ • Standards │ │ • @service          │  │
│  │ • Lifecycle │ │ • Validation│ │ • @dependency       │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Key Features

### **1. Modular System**
- **Self-contained modules** with clear boundaries
- **Automatic dependency resolution** and initialization
- **Hot reloading** without application restarts
- **Lifecycle management** (initialize, enable, disable, cleanup)

### **2. Service Layer**
- **Business logic encapsulation** in services
- **Health monitoring** and circuit breakers
- **Fallback mechanisms** and fault tolerance
- **Performance metrics** and caching

### **3. Configuration Management**
- **Centralized settings** with validation
- **Environment-specific** configurations
- **Module-specific** settings
- **Hot configuration** updates

### **4. Health & Monitoring**
- **Real-time health checks** for modules and services
- **Performance metrics** collection
- **Dependency graph** visualization
- **Alert system** for failures

## 📁 Project Structure

```
core/
├── architecture/           # Core modular system
│   ├── __init__.py
│   ├── base.py            # BaseModule, ModuleRegistry
│   ├── interfaces.py      # Module and service interfaces
│   ├── decorators.py      # Registration decorators
│   └── exceptions.py      # Custom exceptions
├── services/              # Service layer
│   ├── __init__.py
│   ├── base_service.py    # BaseService class
│   ├── service_registry.py # ServiceRegistry
│   └── service_manager.py # ServiceManager
├── modules/               # Application modules
│   ├── __init__.py
│   ├── design_system_module.py
│   ├── security_module.py
│   └── marketplace_module.py
├── config/                # Configuration management
│   ├── __init__.py
│   ├── settings_manager.py
│   ├── config_validator.py
│   └── environment_manager.py
├── design_system.py       # Design system (existing)
├── templatetags/          # Template tags (existing)
└── admin.py              # Admin interface (existing)
```

## 🛠️ Usage Examples

### **1. Creating a Module**

```python
from core.architecture.base import BaseModule
from core.architecture.decorators import module, dependency

@module(
    name="my_module",
    version="1.0.0",
    description="My awesome module",
    dependencies=["design_system"]
)
class MyModule(BaseModule):
    
    def initialize(self) -> bool:
        """Initialize the module."""
        # Set up models, signals, etc.
        return True
    
    def cleanup(self) -> bool:
        """Clean up the module."""
        # Clean up resources
        return True
```

### **2. Creating a Service**

```python
from core.services.base_service import BaseService

class MyService(BaseService):
    service_name = "my_service"
    version = "1.0.0"
    
    def initialize(self) -> bool:
        """Initialize the service."""
        # Set up connections, validate config
        return True
    
    def cleanup(self) -> bool:
        """Clean up the service."""
        # Close connections, clean up resources
        return True
    
    def my_operation(self, data):
        """Business logic operation."""
        return self.retry_operation(self._do_operation, data)
    
    def _do_operation(self, data):
        """Actual operation implementation."""
        # Your business logic here
        pass
```

### **3. Module Dependencies**

```python
@dependency("design_system", required=True)
@dependency("security", required=False)
class DependentModule(BaseModule):
    pass
```

### **4. Configuration Management**

```python
from core.config import settings_manager

# Register module settings
settings_manager.register_module_settings("my_module", {
    "api_key": "your-api-key",
    "timeout": 30,
    "retry_attempts": 3
})

# Get settings
api_key = settings_manager.get_setting("api_key", module_name="my_module")
timeout = settings_manager.get_setting("timeout", default=60)
```

### **5. Service Operations**

```python
from core.services import service_manager

# Call service with fallback
result = service_manager.call_service_with_fallback(
    "primary_service",
    "operation_name",
    fallback_service="backup_service",
    data=data
)

# Check service health
health = service_manager.get_service_health_summary()
```

## 🔧 Configuration

### **Environment Variables**

```bash
# Module configuration
MODULE_DESIGN_SYSTEM_THEME_FILE=themes/custom.json
MODULE_DESIGN_SYSTEM_CACHE_TIMEOUT=7200

# Service configuration
SERVICE_MY_SERVICE_API_KEY=your-api-key
SERVICE_MY_SERVICE_TIMEOUT=30
```

### **Django Settings**

```python
# settings.py

MODULE_CONFIGS = {
    'design_system': {
        'theme_file': 'themes/custom.json',
        'cache_timeout': 7200,
        'auto_reload': True
    },
    'security': {
        'max_login_attempts': 5,
        'lockout_duration': 300
    }
}

SERVICE_CONFIGS = {
    'my_service': {
        'api_key': 'your-api-key',
        'timeout': 30,
        'retry_attempts': 3
    }
}
```

## 📊 Monitoring & Health

### **Module Health**

```python
from core.architecture import ModuleRegistry

# Get all module information
modules_info = ModuleRegistry.get_module_info()

# Get specific module health
module = ModuleRegistry.get_module("design_system")
health = module.get_module_health()
```

### **Service Health**

```python
from core.services import ServiceRegistry

# Get all service information
services_info = ServiceRegistry.get_service_info()

# Get service health summary
health_summary = ServiceRegistry.get_service_health_summary()
```

### **System Health**

```python
from django.apps import apps

marketplace_app = apps.get_app_config('marketplace')
system_health = marketplace_app.get_system_health()
```

## 🚀 Management Commands

### **Module Management**

```bash
# List all modules
python manage.py list_modules

# Enable/disable modules
python manage.py enable_module design_system
python manage.py disable_module design_system

# Reload modules
python manage.py reload_module design_system

# Module health check
python manage.py check_modules
```

### **Service Management**

```bash
# List all services
python manage.py list_services

# Service health check
python manage.py check_services

# Reload services
python manage.py reload_service my_service
```

### **System Management**

```bash
# System health check
python manage.py system_health

# Configuration validation
python manage.py validate_config

# Export configuration
python manage.py export_config

# Import configuration
python manage.py import_config config.json
```

## 🔒 Security Features

### **Permission System**

```python
class MyModule(BaseModule):
    def get_permissions(self) -> Dict[str, List[str]]:
        return {
            'admin': ['my_module.change_config'],
            'user': ['my_module.view_data'],
            'guest': ['my_module.view_public']
        }
```

### **Configuration Validation**

```python
# Add validation rules
settings_manager.add_validation_rule(
    "my_module",
    "api_key",
    {
        "type": "string",
        "required": True,
        "min_length": 32,
        "max_length": 64
    }
)
```

## 📈 Performance Features

### **Caching**

```python
class MyService(BaseService):
    cache_timeout = 300  # 5 minutes
    
    def get_data(self, key):
        # Try cache first
        cached = self.get_cached(key)
        if cached:
            return cached
        
        # Fetch from source
        data = self._fetch_data(key)
        
        # Cache the result
        self.set_cached(key, data)
        return data
```

### **Circuit Breakers**

```python
# Circuit breaker automatically manages service failures
# After 5 failures, service is marked as unavailable
# After 60 seconds, service is marked as half-open
# After successful operation, service is marked as available
```

### **Retry Logic**

```python
class MyService(BaseService):
    retry_attempts = 3
    retry_delay = 1.0  # seconds
    
    def operation(self, data):
        return self.retry_operation(self._do_operation, data)
```

## 🧪 Testing

### **Module Testing**

```python
from django.test import TestCase
from core.architecture import ModuleRegistry

class ModuleTestCase(TestCase):
    def setUp(self):
        # Create test module
        self.module = ModuleRegistry.create_module("test_module")
    
    def test_module_initialization(self):
        self.assertTrue(self.module.initialize())
        self.assertTrue(self.module.is_enabled())
    
    def test_module_cleanup(self):
        self.module.enable()
        self.assertTrue(self.module.cleanup())
        self.assertFalse(self.module.is_enabled())
```

### **Service Testing**

```python
from django.test import TestCase
from core.services import ServiceRegistry

class ServiceTestCase(TestCase):
    def setUp(self):
        # Create test service
        self.service = ServiceRegistry.create_service("test_service")
    
    def test_service_health(self):
        health = self.service.get_health_status()
        self.assertIn('healthy', health)
        self.assertIn('initialized', health)
```

## 🔄 Migration from Existing Code

### **1. Update Django Settings**

```python
# settings.py

INSTALLED_APPS = [
    # ... existing apps ...
    'marketplace.apps.MarketplaceConfig',  # Use new app config
]

# Add module configurations
MODULE_CONFIGS = {
    'design_system': {
        'theme_file': 'core/themes/custom_theme.json',
        'cache_timeout': 3600
    }
}
```

### **2. Update Existing Views**

```python
# Before
from core.design_system import get_design_system

def my_view(request):
    design_system = get_design_system()
    # ... rest of view

# After (optional - still works)
from core.design_system import get_design_system

def my_view(request):
    design_system = get_design_system()
    # ... rest of view

# Or use module directly
from core.architecture import ModuleRegistry

def my_view(request):
    design_module = ModuleRegistry.get_module("design_system")
    theme_info = design_module.get_theme_info()
    # ... rest of view
```

### **3. Update Existing Models**

```python
# Models continue to work as before
# No changes needed for existing models
```

## 🚨 Troubleshooting

### **Common Issues**

1. **Module Not Found**
   ```bash
   # Check if module is registered
   python manage.py list_modules
   
   # Check module dependencies
   python manage.py check_modules
   ```

2. **Service Unavailable**
   ```bash
   # Check service health
   python manage.py check_services
   
   # Check service configuration
   python manage.py validate_config
   ```

3. **Configuration Errors**
   ```bash
   # Validate all settings
   python manage.py validate_config
   
   # Check environment variables
   python manage.py show_env
   ```

### **Debug Mode**

```python
# settings.py
DEBUG = True

# Enable detailed logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'core.architecture': {'level': 'DEBUG'},
        'core.services': {'level': 'DEBUG'},
        'core.modules': {'level': 'DEBUG'},
    },
}
```

## 📚 API Reference

### **ModuleRegistry**

```python
# Register module class
ModuleRegistry.register(MyModuleClass)

# Create module instance
module = ModuleRegistry.create_module("module_name", **config)

# Get module
module = ModuleRegistry.get_module("module_name")

# Initialize all modules
ModuleRegistry.initialize_all()

# Get module information
info = ModuleRegistry.get_module_info()
```

### **ServiceRegistry**

```python
# Register service class
ServiceRegistry.register(MyServiceClass)

# Create service instance
service = ServiceRegistry.create_service("service_name", **config)

# Get service
service = ServiceRegistry.get_service("service_name")

# Get service health
health = ServiceRegistry.get_service_health_summary()
```

### **SettingsManager**

```python
# Get setting
value = settings_manager.get_setting("setting_name", default="default_value")

# Set setting
settings_manager.set_setting("setting_name", "value", module_name="module")

# Register module settings
settings_manager.register_module_settings("module", {"key": "value"})

# Validate settings
issues = settings_manager.validate_settings()
```

## 🤝 Contributing

### **Adding New Modules**

1. Create module class inheriting from `BaseModule`
2. Implement required methods (`initialize`, `cleanup`)
3. Add decorators for metadata and capabilities
4. Register in `marketplace/apps.py`

### **Adding New Services**

1. Create service class inheriting from `BaseService`
2. Implement required methods (`initialize`, `cleanup`)
3. Add business logic methods
4. Register with `ServiceRegistry`

### **Adding New Interfaces**

1. Create interface class inheriting from appropriate base
2. Define required methods
3. Update existing modules to implement interface
4. Add to `core/architecture/interfaces.py`

## 📄 License

This modular architecture is part of your Django project and follows the same license terms.

---

**Happy Modular Development! 🚀✨**