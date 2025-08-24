"""
Product service with optimized operations
"""
from django.db import transaction
from django.db.models import Q, F, Count, Avg
from django.core.cache import cache
from products.models import Product, Category
from django.views.decorators.cache import cache_page
import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class ProductService:
    """Service layer for product operations"""
    
    @staticmethod
    def get_active_products(category_id=None, vendor_id=None, limit=None):
        """Get active products with optimized queries"""
        queryset = Product.objects.filter(is_available=True).select_related(
            'vendor', 'vendor__user', 'category'
        )
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
            
        # Order by created date
        queryset = queryset.order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
            
        return list(queryset)
    
    @staticmethod
    def get_product_detail(product_id):
        """Get product detail with caching"""
        cache_key = f'product_detail_{product_id}'
        product = cache.get(cache_key)
        
        if product is None:
            try:
                product = Product.objects.select_related(
                    'vendor', 'vendor__user', 'category'
                ).get(id=product_id, is_available=True)
                
                cache.set(cache_key, product, 300)  # 5 minute cache
            except Product.DoesNotExist:
                return None
                
        return product
    
    @staticmethod
    def update_product_stock(product_id, quantity_change):
        """Update product stock with atomic operations"""
        affected = Product.objects.filter(
            id=product_id,
            stock_quantity__gte=-quantity_change  # Ensure enough stock
        ).update(
            stock_quantity=F('stock_quantity') + quantity_change
        )
        
        if affected == 0:
            return False  # Insufficient stock
            
        # Invalidate caches
        cache.delete(f'product_detail_{product_id}')
        
        return True
    
    @staticmethod
    def search_products(query, filters=None):
        """Search products with full-text search"""
        # Basic search implementation
        # In production, consider using PostgreSQL full-text search or Elasticsearch
        
        queryset = Product.objects.filter(is_available=True)
        
        # Search in name and description
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query)
            )
        
        # Apply filters
        if filters:
            if filters.get('min_price'):
                queryset = queryset.filter(price_btc__gte=filters['min_price'])
            if filters.get('max_price'):
                queryset = queryset.filter(price_btc__lte=filters['max_price'])
            if filters.get('category_id'):
                queryset = queryset.filter(category_id=filters['category_id'])
            if filters.get('vendor_id'):
                queryset = queryset.filter(vendor_id=filters['vendor_id'])
        
        # Optimize query
        queryset = QueryOptimizer.optimize_product_queryset(queryset)
        
        return queryset
    
    @staticmethod
    def get_trending_products(limit=10):
        """Get trending products based on recent sales"""
        cache_key = f"trending_products:{limit}"
        products = cache.get(cache_key)
        
        if products is None:
            # Get products with recent sales
            products = Product.objects.filter(
                is_available=True,
                orderitem__order__status='completed',
                orderitem__created_at__gte=timezone.now() - timedelta(days=7)
            ).annotate(
                recent_sales=Count('orderitem')
            ).order_by('-recent_sales')[:limit]
            
            # Optimize queryset
            products = products.select_related('vendor', 'vendor__user', 'category')
            cache.set(cache_key, list(products), 60)  # 1 minute cache
            
        return products
    
    @staticmethod
    def get_similar_products(product_id, limit=6):
        """Get similar products based on category and tags"""
        try:
            product = ProductService.get_product_detail(product_id)
            
            similar = Product.objects.filter(
                is_available=True,
                category=product.category
            ).exclude(
                id=product_id
            ).order_by('-avg_rating', '-total_sales')[:limit]
            
            return similar.select_related('vendor', 'vendor__user', 'category')
            
        except Exception:
            return []
