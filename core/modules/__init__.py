"""
Core Modules Package
Provides modular functionality for the system.
"""

from .design_system_module import DesignSystemModule
from .accounts_module import AccountsModule
from .wallets_module import WalletsModule
from .example_module import ExampleModule

__all__ = [
    'DesignSystemModule',
    'AccountsModule',
    'WalletsModule',
    'ExampleModule'
]