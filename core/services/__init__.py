"""
Core Services Package
Provides service layer functionality for the modular system.
"""

from .service_registry import ServiceRegistry
from .base_service import BaseService
from .service_manager import ServiceManager
from .user_service import UserService
from .wallet_service import WalletService
from .vendor_service import VendorService
from .product_service import ProductService
from .order_service import OrderService
from .dispute_service import DisputeService
from .messaging_service import MessagingService
from .support_service import SupportService

__all__ = [
    'ServiceRegistry',
    'BaseService',
    'ServiceManager',
    'UserService',
    'WalletService',
    'VendorService',
    'ProductService',
    'OrderService',
    'DisputeService',
    'MessagingService',
    'SupportService'
]