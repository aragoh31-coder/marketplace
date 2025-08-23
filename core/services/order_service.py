"""
Order Service
Handles all order-related business logic and operations.
"""

from typing import Dict, List, Any, Optional, Tuple
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.utils import timezone
from django.core.cache import cache
from .base_service import BaseService
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
User = get_user_model()


class OrderService(BaseService):
    """Service for managing orders and order operations."""
    
    service_name = "order_service"
    version = "1.0.0"
    description = "Order management and operations service"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._order_cache = {}
        self._order_item_cache = {}
    
    def initialize(self) -> bool:
        """Initialize the order service."""
        try:
            # Set up any connections or validate configuration
            logger.info("Order service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize order service: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up the order service."""
        try:
            # Clear caches
            self._order_cache.clear()
            self._order_item_cache.clear()
            logger.info("Order service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup order service: {e}")
            return False
    
    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ['order_timeout_minutes', 'max_order_items']
    
    def get_order_by_id(self, order_id: str) -> Optional[Any]:
        """Get order by ID with caching."""
        cache_key = f"order:{order_id}"
        
        # Try cache first
        cached_order = self.get_cached(cache_key)
        if cached_order:
            return cached_order
        
        try:
            from orders.models import Order
            order = Order.objects.get(id=order_id)
            
            # Cache order for 5 minutes
            self.set_cached(cache_key, order, timeout=300)
            return order
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    def get_orders_by_user(self, user_id: str, **filters) -> List[Any]:
        """Get orders by user with optional filters."""
        try:
            from orders.models import Order
            
            queryset = Order.objects.filter(user_id=user_id)
            
            # Apply filters
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            
            if filters.get('active_only', False):
                queryset = queryset.exclude(status__in=['completed', 'cancelled'])
            
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])
            
            # Order by creation date
            orders = queryset.order_by('-created_at')
            
            # Apply limit if specified
            if filters.get('limit'):
                orders = orders[:filters['limit']]
            
            return list(orders)
            
        except Exception as e:
            logger.error(f"Failed to get orders for user {user_id}: {e}")
            return []
    
    def get_orders_by_vendor(self, vendor_id: str, **filters) -> List[Any]:
        """Get orders by vendor with optional filters."""
        try:
            from orders.models import Order
            
            queryset = Order.objects.filter(vendor_id=vendor_id)
            
            # Apply filters
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            
            if filters.get('active_only', False):
                queryset = queryset.exclude(status__in=['completed', 'cancelled'])
            
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])
            
            # Order by creation date
            orders = queryset.order_by('-created_at')
            
            # Apply limit if specified
            if filters.get('limit'):
                orders = orders[:filters['limit']]
            
            return list(orders)
            
        except Exception as e:
            logger.error(f"Failed to get orders for vendor {vendor_id}: {e}")
            return []
    
    def create_order(self, user_id: str, vendor_id: str, items: List[Dict], 
                    shipping_address: str, **kwargs) -> Tuple[Any, bool, str]:
        """Create a new order."""
        try:
            from orders.models import Order, OrderItem
            from core.services.product_service import ProductService
            from core.services.wallet_service import WalletService
            
            with transaction.atomic():
                # Validate vendor exists and is active
                from core.services.vendor_service import VendorService
                vendor_service = VendorService()
                vendor = vendor_service.get_vendor_by_user(vendor_id)
                
                if not vendor:
                    return None, False, "Vendor not found"
                
                if not vendor.is_active or vendor.is_on_vacation:
                    return None, False, "Vendor is not available"
                
                # Validate items and calculate total
                product_service = ProductService()
                total_amount = Decimal('0')
                order_items = []
                
                for item in items:
                    product_id = item.get('product_id')
                    quantity = item.get('quantity', 1)
                    
                    # Check product availability
                    available, message = product_service.check_product_availability(product_id, quantity)
                    if not available:
                        return None, False, f"Product {product_id}: {message}"
                    
                    # Get product details
                    product = product_service.get_product_by_id(product_id)
                    if not product:
                        return None, False, f"Product {product_id} not found"
                    
                    # Calculate item total
                    item_total = product.price * quantity
                    total_amount += item_total
                    
                    order_items.append({
                        'product': product,
                        'quantity': quantity,
                        'price': product.price,
                        'total': item_total
                    })
                
                # Check user wallet balance
                wallet_service = WalletService()
                currency = kwargs.get('currency', 'BTC')
                available_balance, msg = wallet_service.get_available_balance(user_id, currency.lower())
                
                if available_balance < total_amount:
                    return None, False, f"Insufficient balance. Required: {total_amount}, Available: {available_balance}"
                
                # Create order
                order = Order.objects.create(
                    user_id=user_id,
                    vendor_id=vendor_id,
                    total_amount=total_amount,
                    currency=currency,
                    shipping_address=shipping_address,
                    status='pending',
                    **kwargs
                )
                
                # Create order items
                for item_data in order_items:
                    OrderItem.objects.create(
                        order=order,
                        product_id=item_data['product'].id,
                        quantity=item_data['quantity'],
                        price=item_data['price'],
                        total=item_data['total']
                    )
                
                # Move funds to escrow
                success, msg = wallet_service.move_to_escrow(user_id, currency.lower(), total_amount, str(order.id))
                if not success:
                    raise Exception(f"Failed to move funds to escrow: {msg}")
                
                # Update product stock
                for item_data in order_items:
                    product_service.update_product_stock(
                        str(item_data['product'].id),
                        -item_data['quantity'],
                        'adjust'
                    )
                
                # Clear caches
                self.clear_cache(f"user_orders:{user_id}")
                self.clear_cache(f"vendor_orders:{vendor_id}")
                
                logger.info(f"Order created successfully: {order.id} for user {user_id}")
                return order, True, "Order created successfully"
                
        except Exception as e:
            logger.error(f"Failed to create order for user {user_id}: {e}")
            return None, False, str(e)
    
    def update_order_status(self, order_id: str, new_status: str, 
                          admin_user_id: str = None, notes: str = "") -> Tuple[bool, str]:
        """Update order status."""
        try:
            order = self.get_order_by_id(order_id)
            if not order:
                return False, "Order not found"
            
            # Validate status transition
            valid_transitions = self._get_valid_status_transitions(order.status)
            if new_status not in valid_transitions:
                return False, f"Invalid status transition from {order.status} to {new_status}"
            
            with transaction.atomic():
                old_status = order.status
                order.status = new_status
                
                # Update status-specific fields
                if new_status == 'processing':
                    order.processing_started = timezone.now()
                elif new_status == 'shipped':
                    order.shipped_at = timezone.now()
                elif new_status == 'completed':
                    order.completed_at = timezone.now()
                    # Release funds from escrow to vendor
                    self._release_funds_to_vendor(order)
                elif new_status == 'cancelled':
                    order.cancelled_at = timezone.now()
                    # Refund user and restore product stock
                    self._refund_order(order)
                
                order.save()
                
                # Log status change
                self._log_order_status_change(order_id, old_status, new_status, admin_user_id, notes)
                
                # Clear caches
                self.clear_cache(f"order:{order_id}")
                self.clear_cache(f"user_orders:{order.user_id}")
                self.clear_cache(f"vendor_orders:{order.vendor_id}")
                
                logger.info(f"Order {order_id} status updated: {old_status} -> {new_status}")
                return True, f"Order status updated to {new_status}"
                
        except Exception as e:
            logger.error(f"Failed to update order status for {order_id}: {e}")
            return False, str(e)
    
    def _get_valid_status_transitions(self, current_status: str) -> List[str]:
        """Get valid status transitions from current status."""
        transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['completed', 'disputed'],
            'completed': [],  # Final state
            'cancelled': [],  # Final state
            'disputed': ['processing', 'cancelled', 'completed']
        }
        return transitions.get(current_status, [])
    
    def _release_funds_to_vendor(self, order: Any) -> None:
        """Release funds from escrow to vendor."""
        try:
            from core.services.wallet_service import WalletService
            
            wallet_service = WalletService()
            
            # Release funds from user's escrow
            success, msg = wallet_service.release_from_escrow(
                str(order.user_id),
                order.currency.lower(),
                order.total_amount,
                str(order.id)
            )
            
            if success:
                # Add funds to vendor's wallet
                wallet_service.add_funds(
                    str(order.vendor_id),
                    order.currency.lower(),
                    order.total_amount,
                    f"order_{order.id}"
                )
                
                logger.info(f"Funds released to vendor for order {order.id}")
            else:
                logger.error(f"Failed to release funds for order {order.id}: {msg}")
                
        except Exception as e:
            logger.error(f"Failed to release funds to vendor for order {order.id}: {e}")
    
    def _refund_order(self, order: Any) -> None:
        """Refund order and restore product stock."""
        try:
            from core.services.wallet_service import WalletService
            from core.services.product_service import ProductService
            
            wallet_service = WalletService()
            product_service = ProductService()
            
            # Refund user
            success, msg = wallet_service.release_from_escrow(
                str(order.user_id),
                order.currency.lower(),
                order.total_amount,
                str(order.id)
            )
            
            if success:
                # Restore product stock
                for item in order.items.all():
                    product_service.update_product_stock(
                        str(item.product_id),
                        item.quantity,
                        'adjust'
                    )
                
                logger.info(f"Order {order.id} refunded and stock restored")
            else:
                logger.error(f"Failed to refund order {order.id}: {msg}")
                
        except Exception as e:
            logger.error(f"Failed to refund order {order.id}: {e}")
    
    def _log_order_status_change(self, order_id: str, old_status: str, new_status: str, 
                               admin_user_id: str = None, notes: str = "") -> None:
        """Log order status change for audit purposes."""
        try:
            from orders.models import OrderStatusLog
            
            OrderStatusLog.objects.create(
                order_id=order_id,
                old_status=old_status,
                new_status=new_status,
                changed_by_id=admin_user_id,
                notes=notes,
                timestamp=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to log order status change: {e}")
    
    def get_order_summary(self, order_id: str) -> Dict[str, Any]:
        """Get comprehensive order summary."""
        try:
            order = self.get_order_by_id(order_id)
            if not order:
                return {}
            
            # Get order items
            items = []
            for item in order.items.all():
                items.append({
                    'id': str(item.id),
                    'product_id': str(item.product_id),
                    'product_name': item.product.name if hasattr(item, 'product') else 'Unknown',
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'total': float(item.total)
                })
            
            return {
                'id': str(order.id),
                'user_id': str(order.user_id),
                'vendor_id': str(order.vendor_id),
                'status': order.status,
                'total_amount': float(order.total_amount),
                'currency': order.currency,
                'shipping_address': order.shipping_address,
                'items': items,
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat() if hasattr(order, 'updated_at') else None,
                'processing_started': order.processing_started.isoformat() if hasattr(order, 'processing_started') and order.processing_started else None,
                'shipped_at': order.shipped_at.isoformat() if hasattr(order, 'shipped_at') and order.shipped_at else None,
                'completed_at': order.completed_at.isoformat() if hasattr(order, 'completed_at') and order.completed_at else None,
                'cancelled_at': order.cancelled_at.isoformat() if hasattr(order, 'cancelled_at') and order.cancelled_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get order summary for {order_id}: {e}")
            return {}
    
    def get_user_order_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's order history."""
        try:
            orders = self.get_orders_by_user(user_id, limit=limit)
            
            return [
                {
                    'id': str(order.id),
                    'vendor_id': str(order.vendor_id),
                    'status': order.status,
                    'total_amount': float(order.total_amount),
                    'currency': order.currency,
                    'created_at': order.created_at.isoformat(),
                    'item_count': order.items.count()
                }
                for order in orders
            ]
            
        except Exception as e:
            logger.error(f"Failed to get order history for user {user_id}: {e}")
            return []
    
    def get_vendor_order_summary(self, vendor_id: str) -> Dict[str, Any]:
        """Get summary of vendor's orders."""
        try:
            from orders.models import Order
            
            orders = Order.objects.filter(vendor_id=vendor_id)
            
            total_orders = orders.count()
            pending_orders = orders.filter(status='pending').count()
            processing_orders = orders.filter(status='processing').count()
            shipped_orders = orders.filter(status='shipped').count()
            completed_orders = orders.filter(status='completed').count()
            cancelled_orders = orders.filter(status='cancelled').count()
            
            # Calculate total revenue
            completed_order_amounts = orders.filter(status='completed').values_list('total_amount', flat=True)
            total_revenue = sum(amount for amount in completed_order_amounts)
            
            # Get recent orders
            recent_orders = orders.order_by('-created_at')[:10]
            recent_order_summaries = [
                {
                    'id': str(o.id),
                    'user_id': str(o.user_id),
                    'status': o.status,
                    'total_amount': float(o.total_amount),
                    'currency': o.currency,
                    'created_at': o.created_at.isoformat()
                }
                for o in recent_orders
            ]
            
            return {
                'vendor_id': vendor_id,
                'total_orders': total_orders,
                'order_statuses': {
                    'pending': pending_orders,
                    'processing': processing_orders,
                    'shipped': shipped_orders,
                    'completed': completed_orders,
                    'cancelled': cancelled_orders
                },
                'total_revenue': float(total_revenue),
                'recent_orders': recent_order_summaries
            }
            
        except Exception as e:
            logger.error(f"Failed to get vendor order summary for {vendor_id}: {e}")
            return {}
    
    def cancel_order(self, order_id: str, user_id: str, reason: str = "") -> Tuple[bool, str]:
        """Cancel an order."""
        try:
            order = self.get_order_by_id(order_id)
            if not order:
                return False, "Order not found"
            
            # Check if user can cancel this order
            if str(order.user_id) != user_id:
                return False, "You can only cancel your own orders"
            
            if order.status not in ['pending', 'processing']:
                return False, f"Order cannot be cancelled in status: {order.status}"
            
            # Update status to cancelled
            return self.update_order_status(order_id, 'cancelled', user_id, reason)
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False, str(e)
    
    def get_order_statistics(self, user_id: str = None, vendor_id: str = None) -> Dict[str, Any]:
        """Get order statistics."""
        try:
            from orders.models import Order
            
            queryset = Order.objects.all()
            
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            if vendor_id:
                queryset = queryset.filter(vendor_id=vendor_id)
            
            total_orders = queryset.count()
            total_revenue = sum(order.total_amount for order in queryset.filter(status='completed'))
            
            # Status distribution
            status_counts = {}
            for status in ['pending', 'processing', 'shipped', 'completed', 'cancelled', 'disputed']:
                status_counts[status] = queryset.filter(status=status).count()
            
            # Monthly trends (last 12 months)
            monthly_trends = {}
            for i in range(12):
                month_start = timezone.now().replace(day=1) - timezone.timedelta(days=30*i)
                month_end = month_start.replace(day=28) + timezone.timedelta(days=4)
                month_end = month_end.replace(day=1) - timezone.timedelta(days=1)
                
                month_orders = queryset.filter(
                    created_at__gte=month_start,
                    created_at__lte=month_end
                )
                
                monthly_trends[month_start.strftime('%Y-%m')] = {
                    'orders': month_orders.count(),
                    'revenue': float(sum(o.total_amount for o in month_orders.filter(status='completed')))
                }
            
            return {
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'status_distribution': status_counts,
                'monthly_trends': monthly_trends
            }
            
        except Exception as e:
            logger.error(f"Failed to get order statistics: {e}")
            return {}
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            from orders.models import Order
            
            total_orders = Order.objects.count()
            pending_orders = Order.objects.filter(status='pending').count()
            processing_orders = Order.objects.filter(status='processing').count()
            
            return {
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'processing_orders': processing_orders,
                'order_cache_size': len(self._order_cache),
                'order_item_cache_size': len(self._order_item_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {'error': str(e)}