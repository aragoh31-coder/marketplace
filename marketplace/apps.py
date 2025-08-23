"""
Django App Configuration for Marketplace
"""

from django.apps import AppConfig
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class MarketplaceConfig(AppConfig):
    """Main Django AppConfig for the marketplace application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'
    
    def ready(self):
        """Initialize the modular system components."""
        # Import modules
        from core.modules.design_system_module import DesignSystemModule
        from core.modules.accounts_module import AccountsModule
        from core.modules.wallets_module import WalletsModule
        from core.modules.example_module import ExampleModule
        from core.modules.products_module import ProductsModule
        from core.modules.orders_module import OrdersModule

        # Import services
        from core.services.user_service import UserService
        from core.services.wallet_service import WalletService
        from core.services.vendor_service import VendorService
        from core.services.product_service import ProductService
        from core.services.order_service import OrderService
        from core.services.dispute_service import DisputeService
        from core.services.messaging_service import MessagingService
        from core.services.support_service import SupportService

        # Create and register modules
        modules_to_register = [
            DesignSystemModule,
            AccountsModule,
            WalletsModule,
            ExampleModule,
            ProductsModule,
            OrdersModule,
        ]

        # Create and register services
        services_to_register = [
            UserService,
            WalletService,
            VendorService,
            ProductService,
            OrderService,
            DisputeService,
            MessagingService,
            SupportService,
        ]

        # Register services first
        for service_class in services_to_register:
            try:
                ServiceRegistry.register(service_class)
                logger.info(f"Service {service_class.service_name} registered successfully")
            except Exception as e:
                logger.error(f"Failed to register service {service_class.service_name}: {e}")

        # Register modules
        for module_class in modules_to_register:
            try:
                # Register the module class
                ModuleRegistry.register_module(module_class)
                logger.info(f"Module {module_class.name} registered successfully")
                
                # Create and initialize the module instance
                module_instance = module_class()
                if module_instance.initialize():
                    logger.info(f"Module {module_class.name} initialized successfully")
                else:
                    logger.error(f"Failed to initialize module {module_class.name}")
                    
            except Exception as e:
                logger.error(f"Failed to register module {module_class.name}: {e}")

        # Initialize service manager
        try:
            from core.services import service_manager
            service_manager.initialize()
            logger.info("Service manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service manager: {e}")

        logger.info("Marketplace application startup complete")

    def get_modules_info(self) -> dict:
        """Get information about all registered modules."""
        try:
            from core.architecture import ModuleRegistry
            
            modules = ModuleRegistry.get_all_modules()
            return {
                name: {
                    'version': module.version,
                    'description': module.description,
                    'enabled': module.is_enabled(),
                    'dependencies': module.get_dependencies(),
                    'health': module.get_module_health()
                }
                for name, module in modules.items()
            }
        except Exception as e:
            logger.error(f"Failed to get modules info: {e}")
            return {}

    def get_services_info(self) -> dict:
        """Get information about all registered services."""
        try:
            from core.services import ServiceRegistry
            
            services = ServiceRegistry.get_all_services()
            return {
                name: {
                    'version': service.version,
                    'description': service.description,
                    'available': service.is_available(),
                    'health': service.get_service_health()
                }
                for name, service in services.items()
            }
        except Exception as e:
            logger.error(f"Failed to get services info: {e}")
            return {}

    def get_system_health(self) -> dict:
        """Get overall system health status."""
        try:
            from core.architecture import ModuleRegistry
            from core.services import ServiceRegistry
            
            # Check modules
            modules = ModuleRegistry.get_all_modules()
            module_health = {
                'total_modules': len(modules),
                'enabled_modules': len([m for m in modules.values() if m.is_enabled()]),
                'healthy_modules': len([m for m in modules.values() if m.is_enabled() and m.get_module_health().get('status', 'UNKNOWN') == 'HEALTHY'])
            }
            
            # Check services
            services = ServiceRegistry.get_all_services()
            service_health = {
                'total_services': len(services),
                'available_services': len([s for s in services.values() if s.is_available()]),
                'healthy_services': len([s for s in services.values() if s.is_available() and s.get_service_health().get('status', 'UNKNOWN') == 'HEALTHY'])
            }
            
            # Overall status
            overall_status = 'HEALTHY'
            if module_health['enabled_modules'] != module_health['healthy_modules']:
                overall_status = 'DEGRADED'
            if service_health['available_services'] != service_health['healthy_services']:
                overall_status = 'DEGRADED'
            
            return {
                'status': overall_status,
                'modules': module_health,
                'services': service_health,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {'status': 'ERROR', 'error': str(e)}

    def reload_module(self, module_name: str) -> bool:
        """Reload a specific module."""
        try:
            from core.architecture import ModuleRegistry
            
            module = ModuleRegistry.get_module(module_name)
            if not module:
                logger.error(f"Module {module_name} not found")
                return False
            
            # Cleanup and reinitialize
            if module.cleanup():
                if module.initialize():
                    logger.info(f"Module {module_name} reloaded successfully")
                    return True
                else:
                    logger.error(f"Failed to reinitialize module {module_name}")
                    return False
            else:
                logger.error(f"Failed to cleanup module {module_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error reloading module {module_name}: {e}")
            return False

    def reload_service(self, service_name: str) -> bool:
        """Reload a specific service."""
        try:
            from core.services import ServiceRegistry
            
            service = ServiceRegistry.get_service(service_name)
            if not service:
                logger.error(f"Service {service_name} not found")
                return False
            
            # Cleanup and reinitialize
            if service.cleanup():
                if service.initialize():
                    logger.info(f"Service {service_name} reloaded successfully")
                    return True
                else:
                    logger.error(f"Failed to reinitialize service {service_name}")
                    return False
            else:
                logger.error(f"Failed to cleanup service {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error reloading service {service_name}: {e}")
            return False

    def get_module_by_name(self, module_name: str):
        """Get a specific module by name."""
        from core.architecture import ModuleRegistry
        return ModuleRegistry.get_module(module_name)

    def get_service_by_name(self, service_name: str):
        """Get a specific service by name."""
        from core.services import ServiceRegistry
        return ServiceRegistry.get_service(service_name)

    def get_all_modules(self) -> dict:
        """Get all registered modules."""
        from core.architecture import ModuleRegistry
        return ModuleRegistry.get_all_modules()

    def get_all_services(self) -> dict:
        """Get all registered services."""
        from core.services import ServiceRegistry
        return ServiceRegistry.get_all_services()

    def get_enabled_modules(self) -> dict:
        """Get all enabled modules."""
        from core.architecture import ModuleRegistry
        return ModuleRegistry.get_enabled_modules()

    def get_available_services(self) -> dict:
        """Get all available services."""
        from core.services import ServiceRegistry
        return ServiceRegistry.get_available_services()

    def shutdown(self):
        """Shutdown the application gracefully."""
        from core.architecture import ModuleRegistry
        from core.services import service_manager
        
        try:
            logger.info("Starting marketplace application shutdown...")
            
            # Shutdown service manager
            service_manager.shutdown()
            
            # Cleanup all modules
            modules = ModuleRegistry.get_all_modules()
            for module_name, module in modules.items():
                try:
                    if module.is_enabled():
                        module.cleanup()
                        logger.info(f"Module {module_name} cleaned up successfully")
                except Exception as e:
                    logger.error(f"Error cleaning up module {module_name}: {e}")
            
            logger.info("Marketplace application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")

    def get_system_metrics(self) -> dict:
        """Get comprehensive system metrics."""
        try:
            from core.services import service_manager

            return {
                'modules': self.get_modules_info(),
                'services': self.get_services_info(),
                'health': self.get_system_health(),
                'service_metrics': service_manager.get_service_metrics_summary(),
                'architecture_validation': self._validate_system_architecture()
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {'error': str(e)}

    def _validate_system_architecture(self) -> dict:
        """Validate the overall system architecture."""
        try:
            from core.services import service_manager

            return {
                'service_architecture': service_manager.validate_service_architecture(),
                'module_dependencies': self._check_module_dependencies(),
                'service_dependencies': self._check_service_dependencies()
            }
        except Exception as e:
            logger.error(f"Failed to validate system architecture: {e}")
            return {'error': str(e)}

    def _check_module_dependencies(self) -> dict:
        """Check module dependencies and conflicts."""
        try:
            from core.architecture import ModuleRegistry

            modules = ModuleRegistry.get_all_modules()
            dependency_issues = []
            circular_deps = []

            for module_name, module in modules.items():
                # Check if dependencies are satisfied
                for dep in module.get_dependencies():
                    if dep not in modules:
                        dependency_issues.append(f"Module {module_name} missing dependency: {dep}")

            return {
                'total_modules': len(modules),
                'dependency_issues': dependency_issues,
                'circular_dependencies': circular_deps,
                'status': 'HEALTHY' if not dependency_issues else 'ISSUES'
            }
        except Exception as e:
            logger.error(f"Failed to check module dependencies: {e}")
            return {'error': str(e)}

    def _check_service_dependencies(self) -> dict:
        """Check service dependencies and conflicts."""
        try:
            from core.services import ServiceRegistry

            services = ServiceRegistry.get_all_services()
            health_issues = []

            for service_name, service in services.items():
                if not service.is_available():
                    health_issues.append(f"Service {service_name} is unavailable")

            return {
                'total_services': len(services),
                'health_issues': health_issues,
                'status': 'HEALTHY' if not health_issues else 'ISSUES'
            }
        except Exception as e:
            logger.error(f"Failed to check service dependencies: {e}")
            return {'error': str(e)}