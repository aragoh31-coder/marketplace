"""
Custom exception classes for the marketplace
"""


class MarketplaceException(Exception):
    """Base exception for marketplace errors"""
    pass


class ValidationException(MarketplaceException):
    """Raised when validation fails"""
    pass


class InsufficientFundsException(MarketplaceException):
    """Raised when user has insufficient funds"""
    pass


class ProductNotAvailableException(MarketplaceException):
    """Raised when product is not available"""
    pass


class OrderException(MarketplaceException):
    """Base exception for order-related errors"""
    pass


class PaymentException(MarketplaceException):
    """Raised when payment processing fails"""
    pass


class SecurityException(MarketplaceException):
    """Raised for security-related issues"""
    pass


class RateLimitException(SecurityException):
    """Raised when rate limit is exceeded"""
    pass


class AuthenticationException(SecurityException):
    """Raised for authentication failures"""
    pass