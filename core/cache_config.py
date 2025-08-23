"""
Caching configuration and utilities for the marketplace
"""
from django.core.cache import cache
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from functools import wraps
import hashlib
import json


class CacheKeys:
    """Centralized cache key management"""
    
    # Cache key prefixes
    PRODUCT_LIST = "product_list"
    PRODUCT_DETAIL = "product_detail"
    VENDOR_PROFILE = "vendor_profile"
    USER_WALLET = "user_wallet"
    CATEGORY_LIST = "category_list"
    SEARCH_RESULTS = "search_results"
    EXCHANGE_RATES = "exchange_rates"
    
    @staticmethod
    def get_product_list_key(filters=None, page=1):
        """Generate cache key for product list"""
        filter_hash = hashlib.md5(
            json.dumps(filters or {}, sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"{CacheKeys.PRODUCT_LIST}:{filter_hash}:page_{page}"
    
    @staticmethod
    def get_product_detail_key(product_id):
        """Generate cache key for product detail"""
        return f"{CacheKeys.PRODUCT_DETAIL}:{product_id}"
    
    @staticmethod
    def get_vendor_profile_key(vendor_id):
        """Generate cache key for vendor profile"""
        return f"{CacheKeys.VENDOR_PROFILE}:{vendor_id}"
    
    @staticmethod
    def get_user_wallet_key(user_id, currency=None):
        """Generate cache key for user wallet"""
        if currency:
            return f"{CacheKeys.USER_WALLET}:{user_id}:{currency}"
        return f"{CacheKeys.USER_WALLET}:{user_id}"
    
    @staticmethod
    def get_search_key(query, filters=None):
        """Generate cache key for search results"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        filter_hash = hashlib.md5(
            json.dumps(filters or {}, sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"{CacheKeys.SEARCH_RESULTS}:{query_hash}:{filter_hash}"


class CacheTimeouts:
    """Cache timeout configurations"""
    
    # Short-lived caches (seconds)
    VERY_SHORT = 60  # 1 minute
    SHORT = 300  # 5 minutes
    MEDIUM = 900  # 15 minutes
    
    # Long-lived caches
    LONG = 3600  # 1 hour
    VERY_LONG = 86400  # 24 hours
    
    # Specific timeouts
    PRODUCT_LIST = 300  # 5 minutes
    PRODUCT_DETAIL = 600  # 10 minutes
    VENDOR_PROFILE = 1800  # 30 minutes
    CATEGORY_LIST = 3600  # 1 hour
    EXCHANGE_RATES = 300  # 5 minutes
    USER_WALLET = 60  # 1 minute (sensitive data)
    SEARCH_RESULTS = 300  # 5 minutes


def smart_cache(timeout=None, key_func=None, vary_on_user=False):
    """
    Smart caching decorator with automatic key generation
    
    Args:
        timeout: Cache timeout in seconds
        key_func: Function to generate cache key
        vary_on_user: Whether to vary cache by user
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Auto-generate key from function name and args
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args[1:])  # Skip 'self' or 'request'
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Add user variation if needed
            if vary_on_user and hasattr(args[0], 'user'):
                request = args[0]
                if request.user.is_authenticated:
                    cache_key = f"{cache_key}:user_{request.user.id}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_timeout = timeout or CacheTimeouts.MEDIUM
            cache.set(cache_key, result, cache_timeout)
            
            return result
        return wrapper
    return decorator


class CacheInvalidation:
    """Cache invalidation utilities"""
    
    @staticmethod
    def invalidate_product(product_id):
        """Invalidate all caches related to a product"""
        cache.delete(CacheKeys.get_product_detail_key(product_id))
        # Also invalidate product lists (pattern-based deletion)
        cache.delete_pattern(f"{CacheKeys.PRODUCT_LIST}:*")
    
    @staticmethod
    def invalidate_vendor(vendor_id):
        """Invalidate all caches related to a vendor"""
        cache.delete(CacheKeys.get_vendor_profile_key(vendor_id))
        # Invalidate product lists that might include vendor products
        cache.delete_pattern(f"{CacheKeys.PRODUCT_LIST}:*")
    
    @staticmethod
    def invalidate_user_wallet(user_id):
        """Invalidate user wallet caches"""
        cache.delete_pattern(f"{CacheKeys.USER_WALLET}:{user_id}:*")
    
    @staticmethod
    def invalidate_search_cache():
        """Invalidate all search result caches"""
        cache.delete_pattern(f"{CacheKeys.SEARCH_RESULTS}:*")


# View decorators for common caching patterns
cache_product_list = cache_page(CacheTimeouts.PRODUCT_LIST)
cache_product_detail = cache_page(CacheTimeouts.PRODUCT_DETAIL)
cache_vendor_profile = cache_page(CacheTimeouts.VENDOR_PROFILE)


class CachedQuerySet:
    """Wrapper for caching QuerySet results"""
    
    def __init__(self, queryset, cache_key, timeout=None):
        self.queryset = queryset
        self.cache_key = cache_key
        self.timeout = timeout or CacheTimeouts.MEDIUM
    
    def get(self):
        """Get cached queryset results"""
        results = cache.get(self.cache_key)
        if results is None:
            results = list(self.queryset)
            cache.set(self.cache_key, results, self.timeout)
        return results
    
    def invalidate(self):
        """Invalidate the cache"""
        cache.delete(self.cache_key)