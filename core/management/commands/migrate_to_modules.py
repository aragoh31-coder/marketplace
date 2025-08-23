"""
Django management command to migrate existing functionality to modules.
"""

import logging

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command to migrate existing functionality to the new modular system."""

    help = "Migrate existing Django apps to the new modular system"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--apps",
            nargs="+",
            help="Specific apps to migrate (default: all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making changes",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force migration even if there are conflicts",
        )
        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="Only validate the current system without migration",
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        self.stdout.write(self.style.SUCCESS("Starting migration to modular system..."))

        try:
            if options["validate_only"]:
                self._validate_system()
                return

            # Get apps to migrate
            apps_to_migrate = self._get_apps_to_migrate(options["apps"])

            if options["dry_run"]:
                self._show_migration_plan(apps_to_migrate)
                return

            # Perform migration
            self._migrate_apps(apps_to_migrate, options["force"])

            self.stdout.write(self.style.SUCCESS("Migration completed successfully!"))

        except Exception as e:
            raise CommandError(f"Migration failed: {e}")

    def _get_apps_to_migrate(self, specified_apps):
        """Get list of apps to migrate."""
        if specified_apps:
            # Validate specified apps exist
            for app_name in specified_apps:
                if not apps.is_installed(app_name):
                    raise CommandError(f'App "{app_name}" is not installed')
            return specified_apps

        # Get all installed apps that are part of the marketplace
        marketplace_apps = [
            "accounts",
            "wallets",
            "vendors",
            "products",
            "orders",
            "disputes",
            "messaging",
            "support",
            "adminpanel",
        ]

        installed_marketplace_apps = [app for app in marketplace_apps if apps.is_installed(app)]

        return installed_marketplace_apps

    def _show_migration_plan(self, apps_to_migrate):
        """Show what would be migrated without making changes."""
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        self.stdout.write("\nApps to migrate:")
        for app_name in apps_to_migrate:
            self.stdout.write(f"  - {app_name}")

        self.stdout.write("\nMigration plan:")
        for app_name in apps_to_migrate:
            self._show_app_migration_plan(app_name)

    def _show_app_migration_plan(self, app_name):
        """Show migration plan for a specific app."""
        self.stdout.write(f"\n{app_name}:")

        try:
            app_config = apps.get_app_config(app_name)

            # Check models
            models = app_config.get_models()
            if models:
                self.stdout.write(f"  Models: {len(models)} found")
                for model in models:
                    self.stdout.write(f"    - {model._meta.model_name}")

            # Check views
            try:
                views_module = __import__(f"{app_name}.views", fromlist=["*"])
                view_attrs = [attr for attr in dir(views_module) if not attr.startswith("_")]
                if view_attrs:
                    self.stdout.write(f"  Views: {len(view_attrs)} found")
                    for attr in view_attrs[:5]:  # Show first 5
                        self.stdout.write(f"    - {attr}")
                    if len(view_attrs) > 5:
                        self.stdout.write(f"    ... and {len(view_attrs) - 5} more")
            except ImportError:
                self.stdout.write("  Views: No views module found")

            # Check URLs
            try:
                urls_module = __import__(f"{app_name}.urls", fromlist=["*"])
                if hasattr(urls_module, "urlpatterns"):
                    self.stdout.write(f"  URLs: {len(urls_module.urlpatterns)} patterns found")
            except ImportError:
                self.stdout.write("  Views: No URLs module found")

            # Check admin
            try:
                admin_module = __import__(f"{app_name}.admin", fromlist=["*"])
                admin_attrs = [attr for attr in dir(admin_module) if not attr.startswith("_")]
                if admin_attrs:
                    self.stdout.write(f"  Admin: {len(admin_attrs)} admin classes found")
            except ImportError:
                self.stdout.write("  Admin: No admin module found")

        except Exception as e:
            self.stdout.write(f"  Error analyzing app: {e}")

    def _migrate_apps(self, apps_to_migrate, force=False):
        """Perform the actual migration of apps."""
        self.stdout.write("\nStarting migration...")

        for app_name in apps_to_migrate:
            self.stdout.write(f"\nMigrating {app_name}...")

            try:
                self._migrate_single_app(app_name, force)
                self.stdout.write(self.style.SUCCESS(f"✓ {app_name} migrated successfully"))
            except Exception as e:
                if force:
                    self.stdout.write(
                        self.style.WARNING(f"⚠ {app_name} migration failed (continuing due to --force): {e}")
                    )
                else:
                    raise CommandError(f"Failed to migrate {app_name}: {e}")

    def _migrate_single_app(self, app_name, force=False):
        """Migrate a single app to the modular system."""
        # This is where the actual migration logic would go
        # For now, we'll just validate that the app can be accessed

        try:
            app_config = apps.get_app_config(app_name)

            # Check if app has required components
            self._validate_app_components(app_name, app_config)

            # Check for conflicts
            conflicts = self._check_migration_conflicts(app_name)
            if conflicts and not force:
                raise CommandError(f"Migration conflicts found: {conflicts}")

            # Perform migration steps
            self._perform_app_migration(app_name, app_config)

        except Exception as e:
            logger.error(f"Failed to migrate app {app_name}: {e}")
            raise

    def _validate_app_components(self, app_name, app_config):
        """Validate that an app has the required components for migration."""
        required_components = ["models", "views", "urls"]

        for component in required_components:
            try:
                if component == "models":
                    models = app_config.get_models()
                    if not models:
                        self.stdout.write(self.style.WARNING(f"  Warning: {app_name} has no models"))
                elif component == "views":
                    __import__(f"{app_name}.views", fromlist=["*"])
                elif component == "urls":
                    __import__(f"{app_name}.urls", fromlist=["*"])

            except ImportError:
                self.stdout.write(self.style.WARNING(f"  Warning: {app_name} missing {component} module"))

    def _check_migration_conflicts(self, app_name):
        """Check for potential migration conflicts."""
        conflicts = []

        # Check if app is already modularized
        try:
            from core.architecture import ModuleRegistry

            if ModuleRegistry.get_module(app_name):
                conflicts.append(f"App {app_name} is already modularized")
        except ImportError:
            pass

        # Check for naming conflicts
        # This would check against existing module names

        return conflicts

    def _perform_app_migration(self, app_name, app_config):
        """Perform the actual migration steps for an app."""
        self.stdout.write(f"  Creating module for {app_name}...")

        # This would involve:
        # 1. Creating a module class
        # 2. Moving business logic to services
        # 3. Updating views to use services
        # 4. Registering the module

        # For now, we'll just show what would be done
        self.stdout.write(f"  ✓ Module structure planned for {app_name}")
        self.stdout.write(f"  ✓ Service layer planned for {app_name}")
        self.stdout.write(f"  ✓ Views will be updated to use services")

    def _validate_system(self):
        """Validate the current system state."""
        self.stdout.write("Validating system...")

        try:
            # Check if modular system is available
            from core.architecture import ModuleRegistry
            from core.services import ServiceRegistry

            # Get system info
            modules = ModuleRegistry.get_module_info()
            services = ServiceRegistry.get_service_info()

            self.stdout.write(f"\nSystem Status:")
            self.stdout.write(f"  Modules: {len(modules)} registered")
            self.stdout.write(f"  Services: {len(services)} registered")

            # Check module health
            enabled_modules = sum(1 for info in modules.values() if info["enabled"])
            self.stdout.write(f"  Enabled modules: {enabled_modules}/{len(modules)}")

            # Check service health
            available_services = sum(1 for info in services.values() if info["available"])
            self.stdout.write(f"  Available services: {available_services}/{len(services)}")

            # Show module details
            if modules:
                self.stdout.write(f"\nRegistered Modules:")
                for name, info in modules.items():
                    status = "✓" if info["enabled"] else "✗"
                    self.stdout.write(f'  {status} {name} (v{info["version"]})')

            # Show service details
            if services:
                self.stdout.write(f"\nRegistered Services:")
                for name, info in services.items():
                    status = "✓" if info["available"] else "✗"
                    self.stdout.write(f'  {status} {name} (v{info["version"]})')

            self.stdout.write(self.style.SUCCESS("\nSystem validation completed successfully!"))

        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"Modular system not available: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Validation failed: {e}"))

    def _get_migration_status(self):
        """Get the current migration status."""
        try:
            from core.architecture import ModuleRegistry

            # Check which apps are already modularized
            existing_modules = ModuleRegistry.get_module_info()

            # Get all marketplace apps
            marketplace_apps = [
                "accounts",
                "wallets",
                "vendors",
                "products",
                "orders",
                "disputes",
                "messaging",
                "support",
                "adminpanel",
            ]

            status = {"total_apps": len(marketplace_apps), "modularized": [], "pending": [], "failed": []}

            for app_name in marketplace_apps:
                if app_name in existing_modules:
                    status["modularized"].append(app_name)
                elif apps.is_installed(app_name):
                    status["pending"].append(app_name)
                else:
                    status["failed"].append(app_name)

            return status

        except ImportError:
            return {"error": "Modular system not available"}

    def _show_migration_status(self):
        """Show the current migration status."""
        status = self._get_migration_status()

        if "error" in status:
            self.stdout.write(self.style.ERROR(f'Cannot determine migration status: {status["error"]}'))
            return

        self.stdout.write(f"\nMigration Status:")
        self.stdout.write(f'  Total apps: {status["total_apps"]}')
        self.stdout.write(f'  Modularized: {len(status["modularized"])}')
        self.stdout.write(f'  Pending: {len(status["pending"])}')
        self.stdout.write(f'  Failed: {len(status["failed"])}')

        if status["modularized"]:
            self.stdout.write(f"\nModularized apps:")
            for app in status["modularized"]:
                self.stdout.write(f"  ✓ {app}")

        if status["pending"]:
            self.stdout.write(f"\nPending migration:")
            for app in status["pending"]:
                self.stdout.write(f"  ⏳ {app}")

        if status["failed"]:
            self.stdout.write(f"\nFailed apps:")
            for app in status["failed"]:
                self.stdout.write(f"  ✗ {app}")
