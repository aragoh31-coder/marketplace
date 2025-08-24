"""
Database Query Optimization Utilities
Provides optimized querysets with proper select_related and prefetch_related
"""
from django.db.models import Prefetch, Q, Count, Sum, Avg
from products.models import Product, Category
from vendors.models import Vendor, VendorRating
from orders.models import Order, OrderItem, Dispute
from accounts.models import User
from wallets.models import Transaction, Wallet
from messaging.models import Message


class OptimizedQuerysets:
    """Centralized location for optimized database queries"""
    
    @staticmethod
    def get_products_list():
        """Get optimized product list queryset"""
        return Product.objects.filter(
            is_active=True
        ).select_related(
            'vendor',
            'vendor__user',
            'category'
        ).prefetch_related(
            'images'
        ).annotate(
            order_count=Count('orderitem__order', distinct=True)
        )
    
    @staticmethod
    def get_product_detail(product_id):
        """Get optimized product detail queryset"""
        return Product.objects.select_related(
            'vendor',
            'vendor__user',
            'category'
        ).prefetch_related(
            'images',
            'orderitem_set__order__user'
        ).get(id=product_id)
    
    @staticmethod
    def get_vendors_list():
        """Get optimized vendor list queryset"""
        return Vendor.objects.filter(
            is_active=True,
            is_approved=True
        ).select_related(
            'user'
        ).annotate(
            product_count=Count('products', filter=Q(products__is_active=True)),
            avg_rating=Avg('ratings__rating'),
            total_sales=Count('products__orderitem__order', 
                            filter=Q(products__orderitem__order__status='completed'),
                            distinct=True)
        )
    
    @staticmethod
    def get_vendor_detail(vendor_id):
        """Get optimized vendor detail queryset"""
        return Vendor.objects.select_related(
            'user'
        ).prefetch_related(
            Prefetch(
                'products',
                queryset=Product.objects.filter(is_active=True).select_related('category')
            ),
            'ratings__user'
        ).annotate(
            avg_rating=Avg('ratings__rating'),
            total_reviews=Count('ratings'),
            completed_orders=Count(
                'products__orderitem__order',
                filter=Q(products__orderitem__order__status='completed'),
                distinct=True
            )
        ).get(id=vendor_id)
    
    @staticmethod
    def get_user_orders(user):
        """Get optimized user orders queryset"""
        return Order.objects.filter(
            user=user
        ).select_related(
            'buyer_wallet'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related(
                    'product',
                    'product__vendor',
                    'product__vendor__user'
                )
            )
        ).order_by('-created_at')
    
    @staticmethod
    def get_vendor_orders(vendor):
        """Get optimized vendor orders queryset"""
        return Order.objects.filter(
            items__product__vendor=vendor
        ).distinct().select_related(
            'user',
            'buyer_wallet'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.filter(
                    product__vendor=vendor
                ).select_related('product')
            )
        ).order_by('-created_at')
    
    @staticmethod
    def get_user_transactions(user):
        """Get optimized user transactions queryset"""
        return Transaction.objects.filter(
            wallet__user=user
        ).select_related(
            'wallet',
            'wallet__user'
        ).order_by('-created_at')
    
    @staticmethod
    def get_user_messages(user):
        """Get optimized user messages queryset"""
        return Message.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).select_related(
            'sender',
            'recipient',
            'order'
        ).order_by('-created_at')
    
    @staticmethod
    def get_admin_users():
        """Get optimized admin users list"""
        return User.objects.all().select_related(
            'userprofile'
        ).prefetch_related(
            'vendor',
            'wallet'
        ).annotate(
            order_count=Count('orders'),
            message_count=Count('sent_messages') + Count('received_messages')
        )
    
    @staticmethod
    def get_admin_orders():
        """Get optimized admin orders list"""
        return Order.objects.all().select_related(
            'user',
            'buyer_wallet'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related(
                    'product',
                    'product__vendor',
                    'product__vendor__user'
                )
            ),
            'dispute'
        ).order_by('-created_at')
    
    @staticmethod
    def get_active_disputes():
        """Get optimized active disputes queryset"""
        return Dispute.objects.filter(
            status__in=['open', 'escalated']
        ).select_related(
            'order',
            'order__user',
            'order__items__product__vendor__user'
        ).prefetch_related(
            'order__items__product'
        ).order_by('-created_at')


class QueryOptimizer:
    """Helper class for query optimization"""
    
    @staticmethod
    def optimize_vendor_dashboard(vendor):
        """Get all data needed for vendor dashboard in minimal queries"""
        from django.db import connection
        from django.db.models import F, DecimalField
        
        # Get vendor stats in one query
        stats = Order.objects.filter(
            items__product__vendor=vendor,
            status='completed'
        ).aggregate(
            total_orders=Count('id', distinct=True),
            total_revenue_btc=Sum(
                F('items__quantity') * F('items__price_btc'),
                output_field=DecimalField()
            ),
            total_revenue_xmr=Sum(
                F('items__quantity') * F('items__price_xmr'),
                output_field=DecimalField()
            )
        )
        
        # Get recent orders
        recent_orders = OptimizedQuerysets.get_vendor_orders(vendor)[:10]
        
        # Get low stock products
        low_stock = Product.objects.filter(
            vendor=vendor,
            is_active=True,
            stock_quantity__lte=5
        ).values('id', 'name', 'stock_quantity').order_by('stock_quantity')
        
        # Get active products count
        active_products = Product.objects.filter(
            vendor=vendor,
            is_active=True
        ).count()
        
        return {
            'stats': stats,
            'recent_orders': recent_orders,
            'low_stock': low_stock,
            'active_products': active_products,
            'query_count': len(connection.queries)
        }