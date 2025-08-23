# Migration Guide: Django Marketplace to Modular Architecture

This guide provides step-by-step instructions for migrating your existing Django marketplace application to the new modular architecture.

## Table of Contents

1. [Overview](#overview)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Migration Steps](#migration-steps)
4. [Testing and Validation](#testing-and-validation)
5. [Performance Optimization](#performance-optimization)
6. [Troubleshooting](#troubleshooting)
7. [Post-Migration Tasks](#post-migration-tasks)

## Overview

The new modular architecture provides:
- **Service Layer**: Business logic separated into dedicated services
- **Module System**: Organized functionality with clear dependencies
- **Hot Reloading**: Ability to reload modules without restart
- **Health Monitoring**: Real-time system health and performance metrics
- **Scalability**: Easy to add new features and scale existing ones

## Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] Django 3.2+ installed
- [ ] All existing apps working correctly
- [ ] Database migrations up to date
- [ ] Backup of your current system
- [ ] Development environment ready
- [ ] Test data available

## Migration Steps

### Step 1: Install the Modular System

The modular system is already integrated into your project. Verify the installation:

```bash
# Check if core modules are available
python manage.py shell
>>> from core.architecture import ModuleRegistry
>>> from core.services import ServiceRegistry
>>> print("Modular system is ready!")
```

### Step 2: Validate Current System

Run the migration validation command:

```bash
python manage.py migrate_to_modules --validate-only
```

This will check your current system and identify any issues.

### Step 3: Review Migration Plan

See what will be migrated:

```bash
python manage.py migrate_to_modules --dry-run
```

This shows you exactly what changes will be made without modifying anything.

### Step 4: Execute Migration

Perform the actual migration:

```bash
# Migrate all apps
python manage.py migrate_to_modules

# Or migrate specific apps
python manage.py migrate_to_modules --apps accounts wallets vendors
```

### Step 5: Update Views

Update your existing views to use the new services instead of direct model operations.

#### Before (Old Way):
```python
# views.py
from accounts.models import User

def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    # Direct model operations
    return render(request, 'profile.html', {'user': user})
```

#### After (New Way):
```python
# views.py
from core.services import user_service

def user_profile(request, user_id):
    user = user_service.get_user_by_id(user_id)
    # Using service layer
    return render(request, 'profile.html', {'user': user})
```

### Step 6: Update Templates

Update your templates to use the new template tags and context:

```html
<!-- Before -->
<div class="user-info">
    <h2>{{ user.username }}</h2>
    <p>Balance: {{ user.wallet.balance_btc }} BTC</p>
</div>

<!-- After -->
<div class="user-info">
    <h2>{{ user.username }}</h2>
    <p>Balance: {{ user_balance.btc }} BTC</p>
</div>
```

### Step 7: Update URLs

Ensure your URL patterns are compatible with the new module system:

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('wallets/', include('wallets.urls')),
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),
    # ... other URLs
]
```

## Testing and Validation

### Run the Test Suite

Execute the comprehensive test suite:

```bash
# Run all tests
python manage.py test tests.test_modular_system

# Run specific test classes
python manage.py test tests.test_modular_system.TestServices
python manage.py test tests.test_modular_system.TestModules
```

### Validate System Health

Check the overall system health:

```bash
python manage.py shell
>>> from marketplace.apps import MarketplaceConfig
>>> app = MarketplaceConfig()
>>> health = app.get_system_health()
>>> print(f"System Status: {health['status']}")
```

### Test Individual Modules

Test each module individually:

```bash
python manage.py shell
>>> from core.modules import AccountsModule
>>> module = AccountsModule()
>>> module.initialize()
>>> health = module.get_module_health()
>>> print(f"Module Health: {health}")
```

## Performance Optimization

### Enable Caching

Configure Redis or Memcached for optimal performance:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Monitor Performance

Use the built-in monitoring tools:

```python
# Get performance metrics
from marketplace.apps import MarketplaceConfig
app = MarketplaceConfig()
metrics = app.get_system_metrics()
print(f"Performance: {metrics}")
```

### Optimize Database Queries

The service layer automatically optimizes database queries. Monitor query performance:

```python
# Enable query logging in development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Troubleshooting

### Common Issues

#### 1. Module Import Errors

**Problem**: `ImportError: No module named 'core.architecture'`

**Solution**: Ensure the core package is properly installed and in your Python path.

#### 2. Service Initialization Failures

**Problem**: Services fail to initialize

**Solution**: Check service dependencies and configuration:

```python
# Debug service initialization
from core.services import user_service
service = user_service()
print(f"Required config: {service.get_required_config()}")
```

#### 3. Module Dependency Conflicts

**Problem**: Circular dependencies between modules

**Solution**: Review module dependencies and resolve conflicts:

```python
# Check module dependencies
from core.modules import AccountsModule
module = AccountsModule()
print(f"Dependencies: {module.get_dependencies()}")
```

#### 4. Database Connection Issues

**Problem**: Services can't connect to database

**Solution**: Verify database configuration and connections:

```python
# Test database connection
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT 1")
result = cursor.fetchone()
print(f"Database connection: {'OK' if result else 'FAILED'}")
```

### Debug Mode

Enable debug mode for detailed error information:

```python
# settings.py
DEBUG = True

# Add debug logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Post-Migration Tasks

### 1. Update Documentation

Update your project documentation to reflect the new architecture:

- API documentation
- User guides
- Developer documentation
- Deployment guides

### 2. Monitor System Performance

Set up monitoring for:

- Response times
- Database query performance
- Memory usage
- Error rates

### 3. Train Your Team

Ensure your development team understands:

- How to use the service layer
- How to create new modules
- How to extend existing services
- Best practices for the new architecture

### 4. Plan Future Enhancements

With the modular system in place, plan for:

- New features as separate modules
- Service improvements
- Performance optimizations
- Scalability enhancements

## Advanced Features

### Hot Reloading

Reload modules without restarting the application:

```python
# Reload a specific module
from marketplace.apps import MarketplaceConfig
app = MarketplaceConfig()
app.reload_module('accounts')

# Reload a specific service
app.reload_service('user_service')
```

### Custom Modules

Create new modules for additional functionality:

```python
# my_module.py
from core.architecture.base import BaseModule
from core.architecture.decorators import module

@module(
    name="my_module",
    version="1.0.0",
    description="My custom module",
    author="Your Name",
    dependencies=[]
)
class MyModule(BaseModule):
    def initialize(self):
        # Custom initialization logic
        return True
    
    def cleanup(self):
        # Custom cleanup logic
        return True
```

### Service Extensions

Extend existing services with custom functionality:

```python
# custom_user_service.py
from core.services.user_service import UserService

class CustomUserService(UserService):
    def custom_method(self):
        # Custom functionality
        return "Custom result"
```

## Migration Checklist

Use this checklist to ensure a complete migration:

- [ ] Modular system installed and configured
- [ ] All existing apps migrated to modules
- [ ] Views updated to use services
- [ ] Templates updated for new context
- [ ] URLs configured correctly
- [ ] Database migrations applied
- [ ] Tests passing
- [ ] System health verified
- [ ] Performance monitored
- [ ] Documentation updated
- [ ] Team trained
- [ ] Production deployment tested

## Support and Resources

### Documentation

- [Modular Architecture README](MODULAR_ARCHITECTURE_README.md)
- [Core Architecture Documentation](core/architecture/README.md)
- [Service Layer Documentation](core/services/README.md)

### Testing

- [Test Suite](tests/test_modular_system.py)
- [Test Configuration](tests/README.md)

### Management Commands

- `migrate_to_modules`: Main migration command
- `update_design`: Design system management
- Custom commands for your modules

### Monitoring

- System health checks
- Performance metrics
- Error logging
- Service availability

## Conclusion

The migration to the modular architecture provides a solid foundation for your marketplace application's future growth. The new system offers:

- **Better Organization**: Clear separation of concerns
- **Improved Maintainability**: Easier to modify and extend
- **Enhanced Performance**: Built-in caching and optimization
- **Scalability**: Easy to add new features
- **Monitoring**: Real-time system health and performance

Follow this guide step-by-step, and you'll have a robust, scalable, and maintainable marketplace application running on the new modular architecture.

For additional support or questions, refer to the documentation or create an issue in your project repository.