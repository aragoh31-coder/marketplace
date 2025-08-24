"""
Order service with business logic
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from core.services.base import BaseService
from .models import Order, OrderItem
from products.models import Product
from wallets.models import Wallet


class OrderService(BaseService):
    """Service for order operations"""
    
    @transaction.atomic
    def create_order(self, user, items_data, payment_currency='BTC'):
        """
        Create a new order with validation
        
        Args:
            user: User creating the order
            items_data: List of dicts with product_id and quantity
            payment_currency: BTC or XMR
            
        Returns:
            Order instance
        """
        # Validate user has wallet
        try:
            wallet = user.wallet
        except Wallet.DoesNotExist:
            raise ValidationError("User wallet not found")
        
        # Create order
        order = Order.objects.create(
            user=user,
            buyer_wallet=wallet,
            status='created',
            payment_currency=payment_currency
        )
        
        total_btc = Decimal('0')
        total_xmr = Decimal('0')
        
        # Create order items
        for item_data in items_data:
            product = Product.objects.select_for_update().get(
                id=item_data['product_id'],
                is_available=True
            )
            
            quantity = item_data['quantity']
            
            # Validate stock
            if product.stock_quantity < quantity:
                raise ValidationError(f"Insufficient stock for {product.name}")
            
            # Create order item
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price_btc=product.price_btc,
                price_xmr=product.price_xmr
            )
            
            # Update totals
            total_btc += order_item.price_btc * quantity
            total_xmr += order_item.price_xmr * quantity
            
            # Update product stock
            product.stock_quantity -= quantity
            product.save(update_fields=['stock_quantity'])
        
        # Update order totals
        order.total_btc = total_btc
        order.total_xmr = total_xmr
        order.save(update_fields=['total_btc', 'total_xmr'])
        
        self.log_info(f"Order {order.id} created for user {user.username}")
        return order
    
    @transaction.atomic
    def process_payment(self, order, payment_proof):
        """Process payment for an order"""
        if order.status != 'created':
            raise ValidationError("Order cannot be paid in current status")
        
        # Here you would verify the payment proof
        # For now, just mark as paid
        order.status = 'paid'
        order.payment_proof = payment_proof
        order.save(update_fields=['status', 'payment_proof'])
        
        # Lock funds in escrow
        from orders.escrow import EscrowService
        escrow_service = EscrowService()
        escrow_service.lock_funds(order)
        
        self.log_info(f"Payment processed for order {order.id}")
        return order
    
    def get_user_orders(self, user, status=None):
        """Get orders for a user with optional status filter"""
        queryset = Order.objects.filter(user=user).select_related(
            'buyer_wallet'
        ).prefetch_related(
            'items__product__vendor'
        ).order_by('-created_at')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_vendor_orders(self, vendor, status=None):
        """Get orders containing vendor's products"""
        queryset = Order.objects.filter(
            items__product__vendor=vendor
        ).distinct().select_related(
            'user', 'buyer_wallet'
        ).prefetch_related(
            'items__product'
        ).order_by('-created_at')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @transaction.atomic
    def cancel_order(self, order, reason=""):
        """Cancel an order and refund if needed"""
        if order.status in ['completed', 'cancelled']:
            raise ValidationError("Order cannot be cancelled")
        
        # Refund if payment was made
        if order.status in ['paid', 'shipped']:
            from orders.escrow import EscrowService
            escrow_service = EscrowService()
            escrow_service.refund_buyer(order)
        
        # Restore product stock
        for item in order.items.all():
            product = item.product
            product.stock_quantity += item.quantity
            product.save(update_fields=['stock_quantity'])
        
        # Update order status
        order.status = 'cancelled'
        order.cancellation_reason = reason
        order.save(update_fields=['status', 'cancellation_reason'])
        
        self.log_info(f"Order {order.id} cancelled")
        return order