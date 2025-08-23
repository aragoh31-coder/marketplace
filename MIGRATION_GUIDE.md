# Migration Guide: From Traditional Django to Modular Architecture

This guide explains how to migrate your existing Django marketplace application to the new modular architecture system.

## Overview

The migration process involves:
1. **Extracting business logic** from views and models into service classes
2. **Creating modules** that encapsulate related functionality
3. **Updating views** to use services instead of direct model operations
4. **Registering modules** with the modular system
5. **Testing** the new modular functionality

## Prerequisites

- Django 3.2+ installed
- Existing marketplace application with apps: `accounts`, `wallets`, `vendors`, `products`, `orders`, `disputes`, `messaging`, `support`, `adminpanel`
- Understanding of the new modular architecture (see `MODULAR_ARCHITECTURE_README.md`)

## Migration Steps

### Step 1: Validate Current System

First, check the current state of your system:

```bash
python manage.py migrate_to_modules --validate-only
```

This will show you:
- Which modules are already registered
- Which services are available
- Overall system health

### Step 2: Plan Migration

Run a dry-run to see what would be migrated:

```bash
python manage.py migrate_to_modules --dry-run
```

This will analyze your existing apps and show:
- Models found in each app
- Views and their complexity
- URL patterns
- Admin configurations
- Potential migration conflicts

### Step 3: Migrate Core Apps

Start with the core apps that have the most business logic:

#### 3.1 Accounts App

The accounts app has been migrated to use the `UserService`. Key changes:

**Before (Traditional Django):**
```python
# views.py
def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    context = {
        'user': user,
        'trust_level': user.get_trust_level(),
        'feedback_score': user.feedback_score,
    }
    return render(request, 'accounts/profile.html', context)
```

**After (Modular with Service):**
```python
# views.py
from core.services.user_service import UserService

def user_profile(request, user_id):
    user_service = UserService()
    user_profile = user_service.get_user_statistics(user_id)
    context = {
        'user_profile': user_profile,
    }
    return render(request, 'accounts/profile.html', context)
```

**Service Layer (core/services/user_service.py):**
```python
class UserService(BaseService):
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        user = self.get_user_by_id(user_id)
        if not user:
            return {}
        
        return {
            'username': user.username,
            'trust_level': self.get_user_trust_level(user_id),
            'feedback_score': user.feedback_score,
            'total_trades': user.total_trades,
            # ... more fields
        }
```

#### 3.2 Wallets App

The wallets app has been migrated to use the `WalletService`. Key changes:

**Before:**
```python
# views.py
def wallet_balance(request):
    wallet = Wallet.objects.get(user=request.user)
    context = {
        'btc_balance': wallet.balance_btc,
        'xmr_balance': wallet.balance_xmr,
        'escrow_btc': wallet.escrow_btc,
    }
    return render(request, 'wallets/balance.html', context)
```

**After:**
```python
# views.py
from core.services.wallet_service import WalletService

def wallet_balance(request):
    wallet_service = WalletService()
    wallet_summary = wallet_service.get_wallet_summary(str(request.user.id))
    context = {
        'wallet_summary': wallet_summary,
    }
    return render(request, 'wallets/balance.html', context)
```

**Service Layer (core/services/wallet_service.py):**
```python
class WalletService(BaseService):
    def get_wallet_summary(self, user_id: str) -> Dict[str, Any]:
        wallet = self.get_wallet_by_user(user_id)
        if not wallet:
            return {}
        
        return {
            'balances': {
                'BTC': {
                    'total': str(wallet.balance_btc),
                    'available': str(wallet.balance_btc - wallet.escrow_btc),
                    'escrow': str(wallet.escrow_btc),
                },
                'XMR': {
                    'total': str(wallet.balance_xmr),
                    'available': str(wallet.balance_xmr - wallet.escrow_xmr),
                    'escrow': str(wallet.escrow_xmr),
                }
            },
            # ... more fields
        }
```

### Step 4: Create Additional Services

For apps that haven't been migrated yet, create service classes:

#### 4.1 Vendor Service

```python
# core/services/vendor_service.py
class VendorService(BaseService):
    def get_vendor_profile(self, user_id: str) -> Optional[Any]:
        return self.get_vendor_by_user(user_id)
    
    def create_vendor_profile(self, user_id: str, vendor_name: str, **kwargs):
        # Business logic for creating vendor profiles
        pass
    
    def update_vendor_rating(self, vendor_user_id: str, user_id: str, rating: int):
        # Business logic for rating updates
        pass
```

#### 4.2 Product Service

```python
# core/services/product_service.py
class ProductService(BaseService):
    def get_products_by_vendor(self, vendor_id: str, **filters):
        # Business logic for product retrieval
        pass
    
    def create_product(self, vendor_id: str, product_data: dict):
        # Business logic for product creation
        pass
```

### Step 5: Create Module Classes

For each app, create a module class:

```python
# core/modules/vendors_module.py
@module(
    name="vendors",
    version="2.0.0",
    description="Vendor management module",
    author="Marketplace Team",
    dependencies=["accounts"],
    required_settings=[]
)
@provides_templates("templates/vendors")
@provides_views(
    vendor_profile="vendors.views.VendorProfileView",
    vendor_list="vendors.views.VendorListView"
)
class VendorsModule(BaseModule, ModelInterface, ViewInterface, TemplateInterface):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vendor_service = VendorService(**kwargs)
    
    def initialize(self) -> bool:
        if not self.vendor_service.initialize():
            return False
        return True
    
    # ... implement required methods
```

### Step 6: Update Views

Update your existing views to use services:

```python
# vendors/views.py
from core.services.vendor_service import VendorService

class VendorProfileView(View):
    def get(self, request, vendor_id):
        vendor_service = VendorService()
        vendor_profile = vendor_service.get_vendor_profile(vendor_id)
        
        context = {
            'vendor_profile': vendor_profile,
        }
        return render(request, 'vendors/profile.html', context)
```

### Step 7: Register Modules

Update `marketplace/apps.py` to include new modules:

```python
def _initialize_modular_system(self):
    # Import modules
    from core.modules.vendors_module import VendorsModule
    from core.modules.products_module import ProductsModule
    
    # Import services
    from core.services.vendor_service import VendorService
    from core.services.product_service import ProductService
    
    # Register services
    services_to_register = [
        VendorService,
        ProductService,
    ]
    
    # Register modules
    modules_to_register = [
        VendorsModule,
        ProductsModule,
    ]
    
    # ... registration logic
```

### Step 8: Test Migration

Test each migrated module:

```bash
# Test specific module
python manage.py test core.modules.vendors_module

# Test all modules
python manage.py test core.modules

# Validate system health
python manage.py migrate_to_modules --validate-only
```

## Migration Patterns

### Pattern 1: Simple CRUD Operations

**Before:**
```python
def create_vendor(request):
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.user = request.user
            vendor.save()
            return redirect('vendor_profile', vendor.id)
```

**After:**
```python
def create_vendor(request):
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor_service = VendorService()
            vendor, success, message = vendor_service.create_vendor_profile(
                str(request.user.id),
                form.cleaned_data['vendor_name'],
                **form.cleaned_data
            )
            if success:
                return redirect('vendor_profile', vendor.id)
            else:
                form.add_error(None, message)
```

### Pattern 2: Complex Business Logic

**Before:**
```python
def process_order(request, order_id):
    order = Order.objects.get(id=order_id)
    
    # Complex business logic mixed with view logic
    if order.status == 'pending':
        if order.payment_confirmed():
            order.status = 'processing'
            order.save()
            
            # Send notifications
            send_order_notification(order)
            
            # Update inventory
            update_inventory(order)
            
            return redirect('order_success')
```

**After:**
```python
def process_order(request, order_id):
    order_service = OrderService()
    result = order_service.process_order(order_id)
    
    if result['success']:
        return redirect('order_success')
    else:
        messages.error(request, result['message'])
        return redirect('order_detail', order_id)
```

**Service Layer:**
```python
class OrderService(BaseService):
    def process_order(self, order_id: str) -> Dict[str, Any]:
        try:
            order = self.get_order(order_id)
            
            if order.status != 'pending':
                return {'success': False, 'message': 'Order cannot be processed'}
            
            if not self.payment_confirmed(order):
                return {'success': False, 'message': 'Payment not confirmed'}
            
            # Process order
            self._update_order_status(order, 'processing')
            self._send_notifications(order)
            self._update_inventory(order)
            
            return {'success': True, 'message': 'Order processed successfully'}
            
        except Exception as e:
            logger.error(f"Failed to process order {order_id}: {e}")
            return {'success': False, 'message': 'Order processing failed'}
```

## Testing Strategy

### 1. Unit Tests for Services

```python
# tests/test_services.py
from django.test import TestCase
from core.services.vendor_service import VendorService

class VendorServiceTest(TestCase):
    def setUp(self):
        self.vendor_service = VendorService()
        self.user = User.objects.create_user(username='testuser')
    
    def test_create_vendor_profile(self):
        result = self.vendor_service.create_vendor_profile(
            str(self.user.id),
            'Test Vendor',
            description='Test description'
        )
        
        vendor, success, message = result
        self.assertTrue(success)
        self.assertEqual(vendor.vendor_name, 'Test Vendor')
```

### 2. Integration Tests for Modules

```python
# tests/test_modules.py
from django.test import TestCase
from core.modules.vendors_module import VendorsModule

class VendorsModuleTest(TestCase):
    def setUp(self):
        self.module = VendorsModule()
    
    def test_module_initialization(self):
        self.assertTrue(self.module.initialize())
        self.assertTrue(self.module.vendor_service.is_available())
    
    def test_module_cleanup(self):
        self.module.initialize()
        self.assertTrue(self.module.cleanup())
```

### 3. End-to-End Tests

```python
# tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

class VendorViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username='testuser')
        self.client.force_login(self.user)
    
    def test_vendor_profile_view(self):
        response = self.client.get('/vendors/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendor Profile')
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all service and module classes are properly imported
2. **Circular Dependencies**: Check module dependencies for circular references
3. **Service Initialization**: Verify services initialize properly before modules
4. **Template Errors**: Ensure template directories are correctly specified

### Debug Commands

```bash
# Check module status
python manage.py shell
>>> from marketplace.apps import MarketplaceConfig
>>> app = MarketplaceConfig('marketplace', 'marketplace')
>>> app.get_modules_info()

# Check service status
>>> app.get_services_info()

# Validate system
>>> app.get_system_health()
```

### Logging

Enable debug logging to troubleshoot issues:

```python
# settings.py
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

## Performance Considerations

### 1. Service Caching

Services include built-in caching:

```python
class VendorService(BaseService):
    def get_vendor_by_user(self, user_id: str):
        cache_key = f"vendor:{user_id}"
        
        # Try cache first
        cached_vendor = self.get_cached(cache_key)
        if cached_vendor:
            return cached_vendor
        
        # Fetch from database
        vendor = Vendor.objects.get(user_id=user_id)
        
        # Cache for 5 minutes
        self.set_cached(cache_key, vendor, timeout=300)
        return vendor
```

### 2. Lazy Loading

Modules and services are loaded on-demand:

```python
class VendorsModule(BaseModule):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._vendor_service = None
    
    @property
    def vendor_service(self):
        if self._vendor_service is None:
            self._vendor_service = VendorService()
        return self._vendor_service
```

### 3. Connection Pooling

Services can implement connection pooling for external services:

```python
class ExternalAPIService(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._connection_pool = None
    
    def get_connection(self):
        if not self._connection_pool:
            self._connection_pool = self._create_connection_pool()
        return self._connection_pool.get_connection()
```

## Migration Checklist

- [ ] Validate current system state
- [ ] Plan migration for each app
- [ ] Create service classes for business logic
- [ ] Create module classes for app functionality
- [ ] Update views to use services
- [ ] Register modules and services
- [ ] Test migrated functionality
- [ ] Update documentation
- [ ] Performance testing
- [ ] Rollback plan ready

## Rollback Strategy

If issues arise during migration:

1. **Disable problematic modules** in `marketplace/apps.py`
2. **Revert view changes** to use original logic
3. **Keep service classes** for future use
4. **Gradual re-enabling** of modules after fixes

## Next Steps

After successful migration:

1. **Monitor system performance** and health
2. **Add new modules** for additional functionality
3. **Implement advanced features** like hot reloading
4. **Scale horizontally** by adding more service instances
5. **Implement microservices** for complex operations

## Support

For migration assistance:

1. Check the `MODULAR_ARCHITECTURE_README.md` for architecture details
2. Review the example modules in `core/modules/`
3. Use the migration command: `python manage.py migrate_to_modules --help`
4. Check system logs for detailed error information

---

**Note**: This migration is designed to be gradual and non-disruptive. You can migrate one app at a time while keeping the system functional.