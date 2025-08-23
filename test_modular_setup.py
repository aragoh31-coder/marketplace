#!/usr/bin/env python3
"""
Simple test script to verify the modular system setup.
Run this to check if all components are properly configured.
"""

import os
import sys
from pathlib import Path

import django

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketplace.settings")

# Setup Django
django.setup()


def test_imports():
    """Test if all modular components can be imported."""
    print("Testing imports...")

    try:
        from core.architecture import BaseModule, ModuleRegistry

        print("✓ Core architecture imports successful")
    except ImportError as e:
        print(f"✗ Core architecture import failed: {e}")
        return False

    try:
        from core.services import BaseService, ServiceRegistry

        print("✓ Core services imports successful")
    except ImportError as e:
        print(f"✗ Core services import failed: {e}")
        return False

    try:
        from core.modules import AccountsModule, DesignSystemModule

        print("✓ Core modules imports successful")
    except ImportError as e:
        print(f"✗ Core modules import failed: {e}")
        return False

    try:
        from core.config import SettingsManager

        print("✓ Core config imports successful")
    except ImportError as e:
        print(f"✗ Core config import failed: {e}")
        return False

    return True


def test_registries():
    """Test if registries can be created."""
    print("\nTesting registries...")

    try:
        from core.architecture import ModuleRegistry
        from core.services import ServiceRegistry

        module_registry = ModuleRegistry()
        service_registry = ServiceRegistry()

        print("✓ Module and service registries created successfully")
        return True
    except Exception as e:
        print(f"✗ Registry creation failed: {e}")
        return False


def test_modules():
    """Test if modules can be instantiated."""
    print("\nTesting module instantiation...")

    try:
        from core.modules import AccountsModule, DesignSystemModule

        design_module = DesignSystemModule()
        accounts_module = AccountsModule(max_login_attempts=5, lockout_duration=900)

        print("✓ Design system and accounts modules instantiated successfully")
        return True
    except Exception as e:
        print(f"✗ Module instantiation failed: {e}")
        return False


def test_services():
    """Test if services can be instantiated."""
    print("\nTesting service instantiation...")

    try:
        from core.services import UserService, WalletService

        # Pass required configuration
        user_service = UserService(max_login_attempts=5, lockout_duration=900)
        wallet_service = WalletService(max_daily_withdrawal=1000, withdrawal_cooldown=3600)

        print("✓ User and wallet services instantiated successfully")
        return True
    except Exception as e:
        print(f"✗ Service instantiation failed: {e}")
        return False


def test_config():
    """Test if configuration can be loaded."""
    print("\nTesting configuration...")

    try:
        from core.config import SettingsManager

        settings_manager = SettingsManager()
        print("✓ Settings manager created successfully")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Modular System Setup")
    print("=" * 40)

    tests = [
        test_imports,
        test_registries,
        test_modules,
        test_services,
        test_config,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 40)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Modular system is ready.")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
