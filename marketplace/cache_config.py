"""
Centralized cache configuration for the marketplace
"""
from django.core.cache import cache
from functools import wraps
import hashlib


class CacheKeys:
    """Centralized cache key generation"""
    
    # Prefixes for different cache types
    PAGE_PREFIX = "page"
    PRODUCT_PREFIX = "product"
    VENDOR_PREFIX = "vendor"
    USER_PREFIX = "user"
    SEARCH_PREFIX = "search"
    
    @staticmethod
    def get_page_key(path, query_params=None):
        """Generate cache key for page"""
        key = f"{CacheKeys.PAGE_PREFIX}:{path}"
        if query_params:
            params_hash = hashlib.md5(str(sorted(query_params.items())).encode()).hexdigest()[:8]
            key = f"{key}:{params_hash}"
        return key
    
    @staticmethod
    def get_product_list_key(category=None, vendor=None, page=1):
        """Generate cache key for product list"""
        parts = [CacheKeys.PRODUCT_PREFIX, "list"]
        if category:
            parts.append(f"cat_{category}")
        if vendor:
            parts.append(f"vendor_{vendor}")
        parts.append(f"page_{page}")
        return ":".join(parts)
    
    @staticmethod
    def get_vendor_dashboard_key(vendor_id):
        """Generate cache key for vendor dashboard"""
        return f"{CacheKeys.VENDOR_PREFIX}:dashboard:{vendor_id}"
    
    @staticmethod
    def get_user_cart_key(user_id):
        """Generate cache key for user cart"""
        return f"{CacheKeys.USER_PREFIX}:cart:{user_id}"


class CacheTimeouts:
    """Cache timeout durations in seconds"""
    
    # Page cache timeouts
    HOMEPAGE = 300  # 5 minutes
    PRODUCT_LIST = 60  # 1 minute
    PRODUCT_DETAIL = 300  # 5 minutes
    VENDOR_LIST = 120  # 2 minutes
    VENDOR_DETAIL = 300  # 5 minutes
    
    # Data cache timeouts
    USER_CART = 1800  # 30 minutes
    VENDOR_DASHBOARD = 60  # 1 minute
    SEARCH_RESULTS = 300  # 5 minutes
    
    # Short caches
    FLASH = 10  # 10 seconds
    SHORT = 30  # 30 seconds
    MEDIUM = 300  # 5 minutes
    LONG = 3600  # 1 hour


def cache_page_tor_safe(timeout):
    """
    Custom page cache decorator that's Tor-safe
    Caches only GET requests and respects privacy
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Only cache GET requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)
            
            # Don't cache authenticated pages
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # Generate cache key
            cache_key = CacheKeys.get_page_key(
                request.path,
                request.GET.dict() if request.GET else None
            )
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Generate response
            response = view_func(request, *args, **kwargs)
            
            # Cache successful responses only
            if response.status_code == 200:
                cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def invalidate_product_caches(product_id=None, category_id=None, vendor_id=None):
    """Invalidate product-related caches"""
    patterns = []
    
    if product_id:
        patterns.append(f"{CacheKeys.PRODUCT_PREFIX}:detail:{product_id}")
    
    if category_id:
        patterns.append(f"{CacheKeys.PRODUCT_PREFIX}:list:cat_{category_id}:*")
    
    if vendor_id:
        patterns.append(f"{CacheKeys.PRODUCT_PREFIX}:list:vendor_{vendor_id}:*")
        patterns.append(f"{CacheKeys.VENDOR_PREFIX}:dashboard:{vendor_id}")
    
    # Always invalidate general product list
    patterns.append(f"{CacheKeys.PRODUCT_PREFIX}:list:page_*")
    
    for pattern in patterns:
        cache.delete_pattern(pattern)


def invalidate_vendor_caches(vendor_id):
    """Invalidate vendor-related caches"""
    patterns = [
        f"{CacheKeys.VENDOR_PREFIX}:dashboard:{vendor_id}",
        f"{CacheKeys.VENDOR_PREFIX}:detail:{vendor_id}",
        f"{CacheKeys.VENDOR_PREFIX}:list:*",
        f"{CacheKeys.PRODUCT_PREFIX}:list:vendor_{vendor_id}:*"
    ]
    
    for pattern in patterns:
        cache.delete_pattern(pattern)