"""
Utility functions for the marketplace
"""
import hashlib
import random
import string
from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def generate_random_string(length=32):
    """Generate a random string of specified length"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_secure_token(prefix=""):
    """Generate a secure token with optional prefix"""
    random_part = generate_random_string(32)
    hash_part = hashlib.sha256(random_part.encode()).hexdigest()[:16]
    token = f"{hash_part}{random_part}"
    
    if prefix:
        return f"{prefix}_{token}"
    return token


def paginate_queryset(queryset, page_number, per_page=20):
    """
    Paginate a queryset
    
    Args:
        queryset: Django queryset
        page_number: Page number (1-based)
        per_page: Items per page
        
    Returns:
        Page object
    """
    paginator = Paginator(queryset, per_page)
    
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    
    return page


def format_currency(amount, currency='BTC', decimals=None):
    """
    Format currency amount for display
    
    Args:
        amount: Decimal amount
        currency: Currency code (BTC, XMR)
        decimals: Number of decimal places (auto-detected if None)
        
    Returns:
        Formatted string
    """
    if decimals is None:
        decimals = 8 if currency == 'BTC' else 12
    
    # Ensure we have a Decimal
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # Format with appropriate decimals
    format_str = f"{{:.{decimals}f}}"
    formatted = format_str.format(amount)
    
    # Remove trailing zeros
    formatted = formatted.rstrip('0').rstrip('.')
    
    # Add currency symbol
    if currency == 'BTC':
        return f"₿{formatted}"
    elif currency == 'XMR':
        return f"ɱ{formatted}"
    else:
        return f"{formatted} {currency}"


def sanitize_filename(filename):
    """
    Sanitize a filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.replace('/', '').replace('\\', '')
    
    # Replace problematic characters
    filename = filename.replace(' ', '_')
    filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
    
    # Limit length
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    if ext:
        max_name_length = 100 - len(ext) - 1
        name = name[:max_name_length]
        filename = f"{name}.{ext}"
    else:
        filename = filename[:100]
    
    return filename


def get_client_ip(request):
    """
    Get client IP from request (Tor-safe)
    
    Returns 'tor-user' for Tor users
    """
    # For Tor compatibility, we don't track real IPs
    if request.META.get('HTTP_X_TOR_EXIT'):
        return 'tor-user'
    
    # Check for Tor browser
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'tor' in user_agent:
        return 'tor-user'
    
    # Default to generic identifier
    return 'anonymous-user'


def calculate_fee(amount, fee_percentage=5):
    """
    Calculate marketplace fee
    
    Args:
        amount: Transaction amount
        fee_percentage: Fee percentage (default 5%)
        
    Returns:
        Tuple of (fee_amount, net_amount)
    """
    amount = Decimal(str(amount))
    fee_rate = Decimal(str(fee_percentage)) / Decimal('100')
    
    fee_amount = amount * fee_rate
    net_amount = amount - fee_amount
    
    return fee_amount, net_amount


def mask_address(address, visible_chars=6):
    """
    Mask a cryptocurrency address for display
    
    Args:
        address: Full address
        visible_chars: Number of characters to show at start and end
        
    Returns:
        Masked address like "1abc...xyz"
    """
    if not address or len(address) <= visible_chars * 2:
        return address
    
    start = address[:visible_chars]
    end = address[-visible_chars:]
    return f"{start}...{end}"