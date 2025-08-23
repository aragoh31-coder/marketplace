"""
Enhanced error handling for the marketplace
"""
import logging
import traceback
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError
from django.http import JsonResponse, HttpResponseServerError
from django.shortcuts import render
from django.utils import timezone
from functools import wraps
import sys


# Configure loggers
logger = logging.getLogger('marketplace.errors')
security_logger = logging.getLogger('marketplace.security')
transaction_logger = logging.getLogger('marketplace.transactions')


class MarketplaceError(Exception):
    """Base exception for marketplace-specific errors"""
    error_code = "MARKETPLACE_ERROR"
    user_message = "An error occurred. Please try again."
    log_level = logging.ERROR
    
    def __init__(self, message=None, details=None, user=None):
        self.message = message or self.user_message
        self.details = details or {}
        self.user = user
        self.timestamp = timezone.now()
        super().__init__(self.message)
    
    def log_error(self):
        """Log the error with appropriate context"""
        logger.log(
            self.log_level,
            f"{self.error_code}: {self.message}",
            extra={
                'error_code': self.error_code,
                'details': self.details,
                'user': self.user.username if self.user else None,
                'timestamp': self.timestamp
            }
        )


class SecurityError(MarketplaceError):
    """Security-related errors"""
    error_code = "SECURITY_ERROR"
    user_message = "Security violation detected."
    log_level = logging.WARNING


class WalletError(MarketplaceError):
    """Wallet-related errors"""
    error_code = "WALLET_ERROR"
    user_message = "Transaction could not be processed."


class InsufficientFundsError(WalletError):
    """Insufficient funds error"""
    error_code = "INSUFFICIENT_FUNDS"
    user_message = "Insufficient funds for this transaction."


class ProductNotAvailableError(MarketplaceError):
    """Product availability error"""
    error_code = "PRODUCT_NOT_AVAILABLE"
    user_message = "This product is no longer available."


class OrderProcessingError(MarketplaceError):
    """Order processing error"""
    error_code = "ORDER_PROCESSING_ERROR"
    user_message = "Could not process your order. Please try again."


def safe_transaction(rollback_on_error=True):
    """
    Decorator for safe transaction handling
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from django.db import transaction
            
            try:
                with transaction.atomic():
                    result = func(*args, **kwargs)
                    return result
            except IntegrityError as e:
                logger.error(f"Database integrity error in {func.__name__}: {str(e)}")
                if rollback_on_error:
                    transaction.set_rollback(True)
                raise OrderProcessingError(
                    "Database constraint violation",
                    details={'function': func.__name__, 'error': str(e)}
                )
            except DatabaseError as e:
                logger.error(f"Database error in {func.__name__}: {str(e)}")
                if rollback_on_error:
                    transaction.set_rollback(True)
                raise MarketplaceError(
                    "Database operation failed",
                    details={'function': func.__name__, 'error': str(e)}
                )
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}")
                if rollback_on_error:
                    transaction.set_rollback(True)
                raise
        return wrapper
    return decorator


def handle_errors(error_template='errors/generic.html', log_errors=True):
    """
    Decorator for view error handling
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                return func(request, *args, **kwargs)
            except MarketplaceError as e:
                if log_errors:
                    e.log_error()
                return render(request, error_template, {
                    'error': e,
                    'error_code': e.error_code,
                    'message': e.user_message
                }, status=400)
            except ValidationError as e:
                logger.warning(f"Validation error in {func.__name__}: {str(e)}")
                return render(request, error_template, {
                    'error': e,
                    'error_code': 'VALIDATION_ERROR',
                    'message': 'Invalid input provided.'
                }, status=400)
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}")
                if settings.DEBUG:
                    raise
                return render(request, 'errors/500.html', {
                    'error_id': generate_error_id()
                }, status=500)
        return wrapper
    return decorator


def api_error_handler(func):
    """
    Decorator for API error handling (returns JSON)
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except MarketplaceError as e:
            e.log_error()
            return JsonResponse({
                'error': e.error_code,
                'message': e.user_message,
                'details': e.details if settings.DEBUG else {}
            }, status=400)
        except ValidationError as e:
            return JsonResponse({
                'error': 'VALIDATION_ERROR',
                'message': 'Invalid input',
                'errors': e.message_dict if hasattr(e, 'message_dict') else str(e)
            }, status=400)
        except Exception as e:
            logger.exception(f"API error in {func.__name__}")
            return JsonResponse({
                'error': 'SERVER_ERROR',
                'message': 'An unexpected error occurred',
                'error_id': generate_error_id()
            }, status=500)
    return wrapper


def generate_error_id():
    """Generate unique error ID for tracking"""
    import uuid
    return f"ERR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


class ErrorReporter:
    """Centralized error reporting"""
    
    @staticmethod
    def report_security_incident(incident_type, details, user=None, request=None):
        """Report security incidents"""
        incident = {
            'type': incident_type,
            'timestamp': timezone.now(),
            'details': details,
            'user': user.username if user else None,
        }
        
        if request:
            incident.update({
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'path': request.path,
                'method': request.method
            })
        
        security_logger.warning(f"Security incident: {incident_type}", extra=incident)
        
        # Could also send alerts, save to database, etc.
        return incident
    
    @staticmethod
    def report_transaction_error(error_type, transaction_data, user=None):
        """Report transaction errors"""
        error_data = {
            'error_type': error_type,
            'timestamp': timezone.now(),
            'transaction': transaction_data,
            'user': user.username if user else None,
        }
        
        transaction_logger.error(f"Transaction error: {error_type}", extra=error_data)
        return error_data


def get_client_ip(request):
    """Get client IP address from request - returns 'tor-user' for privacy"""
    # For Tor compatibility, we don't track IP addresses
    return "tor-user"


# Custom error views
def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    """Custom 500 error page"""
    error_id = generate_error_id()
    logger.error(f"500 error: {error_id}", extra={
        'path': request.path,
        'method': request.method,
        'user': request.user.username if request.user.is_authenticated else None
    })
    return render(request, 'errors/500.html', {
        'error_id': error_id
    }, status=500)


def custom_403(request, exception):
    """Custom 403 error page"""
    return render(request, 'errors/403.html', status=403)