"""
Marketplace Application Configuration
Main Django app configuration with modular system integration.
"""

from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MarketplaceConfig(AppConfig):
    """
    Main marketplace application configuration.
    Integrates with the modular system for dynamic functionality.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'
    verbose_name = 'Marketplace'
    
    def ready(self):
        """Initialize the application when Django is ready."""
        # Import here to avoid circular imports
        from core.architecture import ModuleRegistry
        from core.services import ServiceRegistry, service_manager
        from core.config import settings_manager
        
        try:
            # Initialize the modular system
            self._initialize_modular_system()
            
            # Start service monitoring
            service_manager.start_monitoring()
            
            logger.info("Marketplace application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize marketplace application: {e}")
    
    def _initialize_modular_system(self):
        """Initialize the modular system components."""
        # Import modules
        from core.modules.design_system_module import DesignSystemModule
        from core.modules.accounts_module import AccountsModule
        from core.modules.wallets_module import WalletsModule
        from core.modules.example_module import ExampleModule
        
        # Import services
        from core.services.user_service import UserService
        from core.services.wallet_service import WalletService
        from core.services.vendor_service import VendorService
        
        # Create and register modules
        modules_to_register = [
            DesignSystemModule,
            AccountsModule,
            WalletsModule,
            ExampleModule,
        ]
        
        # Create and register services
        services_to_register = [
            UserService,
            WalletService,
            VendorService,
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
                ModuleRegistry.register(module_class)
                
                # Create module instance
                module_instance = ModuleRegistry.create_module(
                    module_class.name,
                    **self._get_module_config(module_class.name)
                )
                
                if module_instance:
                    logger.info(f"Module {module_class.name} registered and created successfully")
                else:
                    logger.error(f"Failed to create module instance for {module_class.name}")
                    
            except Exception as e:
                logger.error(f"Failed to register module {module_class.name}: {e}")
        
        # Initialize all modules
        if not ModuleRegistry.initialize_all():
            logger.error("Failed to initialize all modules")
        
        # Initialize all services
        if not ServiceRegistry.initialize_all():
            logger.error("Failed to initialize all services")
    
    def _get_module_config(self, module_name: str) -> dict:
        """Get configuration for a specific module."""
        # This can be extended to load module-specific configuration
        # from files, environment variables, or database
        config = {}
        
        # Load from environment variables
        import os
        for key, value in os.environ.items():
            if key.startswith(f'MODULE_{module_name.upper()}_'):
                config_key = key.replace(f'MODULE_{module_name.upper()}_', '').lower()
                config[config_key] = value
        
        # Load from settings if available
        if hasattr(settings, 'MODULE_CONFIGS'):
            module_configs = getattr(settings, 'MODULE_CONFIGS', {})
            if module_name in module_configs:
                config.update(module_configs[module_name])
        
        return config
    
    def get_modules_info(self) -> dict:
        """Get information about all registered modules."""
        from core.architecture import ModuleRegistry
        
        return ModuleRegistry.get_module_info()
    
    def get_services_info(self) -> dict:
        """Get information about all registered services."""
        from core.services import ServiceRegistry
        
        return ServiceRegistry.get_service_info()
    
    def get_system_health(self) -> dict:
        """Get overall system health status."""
        from core.architecture import ModuleRegistry
        from core.services import ServiceRegistry
        
        module_info = ModuleRegistry.get_module_info()
        service_info = ServiceRegistry.get_service_info()
        
        # Calculate overall health
        total_modules = len(module_info)
        enabled_modules = sum(1 for info in module_info.values() if info['enabled'])
        
        total_services = len(service_info)
        available_services = sum(1 for info in service_info.values() if info['available'])
        
        module_health = enabled_modules / total_modules if total_modules > 0 else 0
        service_health = available_services / total_services if total_services > 0 else 0
        
        overall_health = (module_health + service_health) / 2
        
        return {
            'overall_health': overall_health,
            'module_health': module_health,
            'service_health': service_health,
            'total_modules': total_modules,
            'enabled_modules': enabled_modules,
            'total_services': total_services,
            'available_services': available_services,
            'status': 'HEALTHY' if overall_health > 0.8 else 'DEGRADED' if overall_health > 0.5 else 'UNHEALTHY'
        }
    
    def reload_module(self, module_name: str) -> bool:
        """Reload a specific module."""
        from core.architecture import ModuleRegistry
        
        try:
            success = ModuleRegistry.reload_module(module_name)
            if success:
                logger.info(f"Module {module_name} reloaded successfully")
            else:
                logger.error(f"Failed to reload module {module_name}")
            return success
        except Exception as e:
            logger.error(f"Error reloading module {module_name}: {e}")
            return False
    
    def reload_service(self, service_name: str) -> bool:
        """Reload a specific service."""
        from core.services import ServiceRegistry
        
        try:
            success = ServiceRegistry.reload_service(service_name)
            if success:
                logger.info(f"Service {service_name} reloaded successfully")
            else:
                logger.error(f"Failed to reload service {service_name}")
            return success
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
        from core.services import ServiceRegistry, service_manager
        
        logger.info("Shutting down marketplace application...")
        
        try:
            # Stop service monitoring
            service_manager.stop_monitoring()
            
            # Cleanup all services
            ServiceRegistry.cleanup_all()
            
            # Cleanup all modules
            ModuleRegistry.cleanup_all()
            
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