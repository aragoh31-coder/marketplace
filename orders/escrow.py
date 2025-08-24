from django.db import transaction
from django.utils import timezone
from wallets.models import Wallet, Transaction
from decimal import Decimal
import logging

logger = logging.getLogger('orders.escrow')


class EscrowService:
    """Service for handling escrow operations"""
    
    @staticmethod
    @transaction.atomic
    def lock_funds(order):
        """Lock buyer's funds in escrow for an order"""
        from .models import Order
        
        if order.status != 'PENDING':
            raise ValueError(f"Cannot lock funds for order in {order.status} status")
            
        # Get buyer's wallet with row lock
        wallet = Wallet.objects.select_for_update().get(user=order.user)
        
        # Determine amount based on currency
        if order.currency_used == 'BTC':
            if wallet.balance_btc < order.total_btc:
                raise ValueError(f"Insufficient BTC balance. Required: {order.total_btc}, Available: {wallet.balance_btc}")
            
            # Move funds from balance to escrow
            wallet.balance_btc -= order.total_btc
            wallet.escrow_btc += order.total_btc
            amount = order.total_btc
            
        elif order.currency_used == 'XMR':
            if wallet.balance_xmr < order.total_xmr:
                raise ValueError(f"Insufficient XMR balance. Required: {order.total_xmr}, Available: {wallet.balance_xmr}")
            
            # Move funds from balance to escrow
            wallet.balance_xmr -= order.total_xmr
            wallet.escrow_xmr += order.total_xmr
            amount = order.total_xmr
            
        else:
            raise ValueError(f"Invalid currency: {order.currency_used}")
        
        wallet.save()
        
        # Update order status
        order.lock_funds()
        
        # Create transaction record
        Transaction.objects.create(
            user=order.user,
            type='escrow_lock',
            amount=amount,
            currency=order.currency_used,
            balance_before=wallet.balance_btc if order.currency_used == 'BTC' else wallet.balance_xmr,
            balance_after=wallet.balance_btc if order.currency_used == 'BTC' else wallet.balance_xmr,
            reference=f"order:{order.id}",
            related_object_type='Order',
            related_object_id=str(order.id),
            metadata={
                'order_id': str(order.id),
                'vendor': order.vendor.user.username if order.vendor else 'Unknown',
                'product_count': order.items.count() if hasattr(order, 'items') else 1
            }
        )
        
        logger.info(f"Locked {amount} {order.currency_used} for order {order.id}")
        return True
    
    @staticmethod
    @transaction.atomic
    def release_funds(order):
        """Release escrowed funds to vendor"""
        from .models import Order
        
        if order.status not in ['SHIPPED', 'LOCKED', 'PROCESSING']:
            raise ValueError(f"Cannot release funds for order in {order.status} status")
            
        if order.escrow_released:
            raise ValueError("Escrow already released for this order")
        
        # Get wallets with row locks
        buyer_wallet = Wallet.objects.select_for_update().get(user=order.user)
        vendor_wallet = Wallet.objects.select_for_update().get(user=order.vendor.user)
        
        # Determine amount and fee
        if order.currency_used == 'BTC':
            amount = order.total_btc
            fee = amount * Decimal('0.02')  # 2% marketplace fee
            vendor_amount = amount - fee
            
            # Move from buyer's escrow to vendor's balance
            buyer_wallet.escrow_btc -= amount
            vendor_wallet.balance_btc += vendor_amount
            
        elif order.currency_used == 'XMR':
            amount = order.total_xmr
            fee = amount * Decimal('0.02')  # 2% marketplace fee
            vendor_amount = amount - fee
            
            # Move from buyer's escrow to vendor's balance
            buyer_wallet.escrow_xmr -= amount
            vendor_wallet.balance_xmr += vendor_amount
            
        else:
            raise ValueError(f"Invalid currency: {order.currency_used}")
        
        buyer_wallet.save()
        vendor_wallet.save()
        
        # Update order status
        order.mark_completed()
        
        # Create transaction records
        Transaction.objects.create(
            user=order.user,
            type='escrow_release',
            amount=-amount,
            currency=order.currency_used,
            balance_before=buyer_wallet.escrow_btc if order.currency_used == 'BTC' else buyer_wallet.escrow_xmr,
            balance_after=buyer_wallet.escrow_btc if order.currency_used == 'BTC' else buyer_wallet.escrow_xmr,
            reference=f"order:{order.id}",
            related_object_type='Order',
            related_object_id=str(order.id)
        )
        
        Transaction.objects.create(
            user=order.vendor.user,
            type='payment_received',
            amount=vendor_amount,
            currency=order.currency_used,
            balance_before=vendor_wallet.balance_btc if order.currency_used == 'BTC' else vendor_wallet.balance_xmr,
            balance_after=vendor_wallet.balance_btc if order.currency_used == 'BTC' else vendor_wallet.balance_xmr,
            reference=f"order:{order.id}",
            related_object_type='Order',
            related_object_id=str(order.id),
            metadata={
                'order_id': str(order.id),
                'buyer': order.user.username,
                'fee': str(fee),
                'gross_amount': str(amount)
            }
        )
        
        logger.info(f"Released {vendor_amount} {order.currency_used} to vendor for order {order.id}")
        return True
    
    @staticmethod
    @transaction.atomic
    def refund_buyer(order, partial_percentage=None):
        """Refund escrowed funds to buyer"""
        from .models import Order
        
        if not order.can_dispute():
            raise ValueError(f"Cannot refund order in {order.status} status")
            
        if order.escrow_released:
            raise ValueError("Escrow already released for this order")
        
        # Get buyer's wallet with row lock
        buyer_wallet = Wallet.objects.select_for_update().get(user=order.user)
        
        # Calculate refund amount
        if order.currency_used == 'BTC':
            full_amount = order.total_btc
            refund_amount = full_amount
            if partial_percentage:
                refund_amount = full_amount * Decimal(partial_percentage) / 100
            
            # Move from escrow back to balance
            buyer_wallet.escrow_btc -= full_amount
            buyer_wallet.balance_btc += refund_amount
            
        elif order.currency_used == 'XMR':
            full_amount = order.total_xmr
            refund_amount = full_amount
            if partial_percentage:
                refund_amount = full_amount * Decimal(partial_percentage) / 100
            
            # Move from escrow back to balance
            buyer_wallet.escrow_xmr -= full_amount
            buyer_wallet.balance_xmr += refund_amount
            
        else:
            raise ValueError(f"Invalid currency: {order.currency_used}")
        
        buyer_wallet.save()
        
        # Update order status
        order.mark_refunded()
        
        # Create transaction record
        Transaction.objects.create(
            user=order.user,
            type='escrow_refund',
            amount=refund_amount,
            currency=order.currency_used,
            balance_before=buyer_wallet.balance_btc if order.currency_used == 'BTC' else buyer_wallet.balance_xmr,
            balance_after=buyer_wallet.balance_btc if order.currency_used == 'BTC' else buyer_wallet.balance_xmr,
            reference=f"order:{order.id}",
            related_object_type='Order',
            related_object_id=str(order.id),
            metadata={
                'order_id': str(order.id),
                'refund_type': 'partial' if partial_percentage else 'full',
                'refund_percentage': partial_percentage if partial_percentage else 100
            }
        )
        
        # Handle partial payment to vendor if applicable
        if partial_percentage and partial_percentage < 100:
            vendor_percentage = 100 - partial_percentage
            vendor_amount = full_amount * Decimal(vendor_percentage) / 100
            
            vendor_wallet = Wallet.objects.select_for_update().get(user=order.vendor.user)
            if order.currency_used == 'BTC':
                vendor_wallet.balance_btc += vendor_amount
            else:
                vendor_wallet.balance_xmr += vendor_amount
            vendor_wallet.save()
            
            Transaction.objects.create(
                user=order.vendor.user,
                type='payment_received',
                amount=vendor_amount,
                currency=order.currency_used,
                balance_before=vendor_wallet.balance_btc if order.currency_used == 'BTC' else vendor_wallet.balance_xmr,
                balance_after=vendor_wallet.balance_btc if order.currency_used == 'BTC' else vendor_wallet.balance_xmr,
                reference=f"order:{order.id}",
                related_object_type='Order',
                related_object_id=str(order.id),
                metadata={
                    'order_id': str(order.id),
                    'payment_type': 'partial_resolution',
                    'percentage': vendor_percentage
                }
            )
        
        logger.info(f"Refunded {refund_amount} {order.currency_used} to buyer for order {order.id}")
        return True