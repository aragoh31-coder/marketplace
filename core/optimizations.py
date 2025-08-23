"""
Query optimization utilities for the marketplace
"""
from django.core.cache import cache
from django.db.models import Prefetch, Count, Q, F, Sum, Avg
from functools import wraps
import hashlib
import json


def cache_query(timeout=300):
    """Decorator to cache query results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute query and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


class QueryOptimizer:
    """Utilities for optimizing database queries"""
    
    @staticmethod
    def optimize_product_queryset(queryset):
        """Optimize product queries with proper joins"""
        return queryset.select_related(
            'vendor',
            'category',
        ).prefetch_related(
            'images',
            'reviews',
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
            total_sales=Count('orderitem', filter=Q(orderitem__order__status='completed'))
        )
    
    @staticmethod
    def optimize_order_queryset(queryset):
        """Optimize order queries"""
        return queryset.select_related(
            'user',
            'vendor',
            'shipping_address',
        ).prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product')),
            'transactions',
        )
    
    @staticmethod
    def optimize_user_queryset(queryset):
        """Optimize user queries"""
        return queryset.prefetch_related(
            'orders',
            'reviews',
            'wallet_set',
        ).annotate(
            total_orders=Count('orders'),
            total_spent=Sum('orders__total_price', filter=Q(orders__status='completed')),
        )
    
    @staticmethod
    def optimize_vendor_queryset(queryset):
        """Optimize vendor queries"""
        return queryset.select_related(
            'user',
        ).prefetch_related(
            'products',
            'orders',
        ).annotate(
            product_count=Count('products', filter=Q(products__is_available=True)),
            total_sales=Count('orders', filter=Q(orders__status='completed')),
            avg_rating=Avg('products__reviews__rating'),
        )


class BulkOperations:
    """Utilities for bulk database operations"""
    
    @staticmethod
    def bulk_update_stock(product_updates):
        """Bulk update product stock levels"""
        products = []
        for product_id, quantity_change in product_updates.items():
            products.append(
                Product.objects.filter(id=product_id).update(
                    stock_quantity=F('stock_quantity') + quantity_change
                )
            )
        return products
    
    @staticmethod
    def bulk_create_notifications(notifications_data):
        """Bulk create notifications"""
        from core.models import Notification
        notifications = [
            Notification(**data) for data in notifications_data
        ]
        return Notification.objects.bulk_create(notifications, batch_size=100)