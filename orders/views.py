from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.views.decorators.http import require_POST
from django.utils import timezone

from products.models import Product
from disputes.models import Dispute
from wallets.models import Wallet

from .models import Cart, CartItem, Order, OrderItem
from .escrow import EscrowService
from .forms import CreateOrderForm


@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related("product")
    
    # Calculate totals
    total_btc = sum(item.product.price_btc * item.quantity for item in cart_items)
    total_xmr = sum(item.product.price_xmr * item.quantity for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_btc': total_btc,
        'total_xmr': total_xmr,
    }
    return render(request, "orders/cart.html", context)


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)

    if product.vendor.is_on_vacation:
        messages.error(request, f"Cannot add {product.name} to cart - vendor is on vacation.")
        return redirect("products:detail", pk=product_id)

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": 1})

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f"{product.name} added to cart!")
    return redirect("products:detail", pk=product_id)


@login_required
@transaction.atomic
def create_order(request):
    """Create order from cart and lock funds"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related('product', 'product__vendor')
    
    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect('orders:cart')
    
    if request.method == 'POST':
        # Get currency choice
        currency = request.POST.get('currency', 'BTC')
        if currency not in ['BTC', 'XMR']:
            messages.error(request, "Invalid currency selection")
            return redirect('orders:cart')
        
        # Group items by vendor
        vendor_items = {}
        for item in cart_items:
            vendor = item.product.vendor
            if vendor not in vendor_items:
                vendor_items[vendor] = []
            vendor_items[vendor].append(item)
        
        # Create separate order for each vendor
        orders_created = []
        
        try:
            for vendor, items in vendor_items.items():
                # Calculate totals for this vendor
                total_btc = sum(item.product.price_btc * item.quantity for item in items)
                total_xmr = sum(item.product.price_xmr * item.quantity for item in items)
                
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    vendor=vendor,
                    total_btc=total_btc,
                    total_xmr=total_xmr,
                    currency_used=currency,
                    shipping_address=request.POST.get('shipping_address', '')
                )
                
                # Create order items
                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price_btc=item.product.price_btc,
                        price_xmr=item.product.price_xmr
                    )
                
                # Lock funds in escrow
                EscrowService.lock_funds(order)
                orders_created.append(order)
            
            # Clear cart after successful order creation
            cart.items.all().delete()
            
            messages.success(request, f"Successfully created {len(orders_created)} order(s) and locked funds in escrow")
            
            # Redirect to first order detail if only one order
            if len(orders_created) == 1:
                return redirect('orders:detail', pk=orders_created[0].id)
            else:
                return redirect('orders:list')
                
        except ValueError as e:
            # Delete any created orders if escrow fails
            for order in orders_created:
                order.delete()
            messages.error(request, str(e))
            return redirect('orders:cart')
        
    # GET request - show order confirmation
    # Calculate totals
    total_btc = sum(item.product.price_btc * item.quantity for item in cart_items)
    total_xmr = sum(item.product.price_xmr * item.quantity for item in cart_items)
    
    # Check wallet balances
    wallet = Wallet.objects.get(user=request.user)
    
    context = {
        'cart_items': cart_items,
        'total_btc': total_btc,
        'total_xmr': total_xmr,
        'wallet': wallet,
        'has_sufficient_btc': wallet.balance_btc >= total_btc,
        'has_sufficient_xmr': wallet.balance_xmr >= total_xmr,
    }
    
    return render(request, 'orders/create.html', context)


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    
    # Separate active and completed orders
    active_orders = orders.filter(status__in=['PENDING', 'PAID', 'LOCKED', 'PROCESSING', 'SHIPPED'])
    completed_orders = orders.filter(status__in=['COMPLETED', 'CANCELLED', 'REFUNDED'])
    disputed_orders = orders.filter(status='DISPUTED')
    
    context = {
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'disputed_orders': disputed_orders,
    }
    return render(request, "orders/list.html", context)


@login_required
def order_detail(request, pk):
    # Allow both buyer and vendor to view order
    order = get_object_or_404(
        Order.objects.select_related('vendor', 'user', 'dispute'),
        pk=pk
    )
    
    # Check permissions
    if request.user != order.user and request.user != order.vendor.user:
        messages.error(request, "You don't have permission to view this order")
        return redirect('orders:list')
    
    # Get order items
    order_items = order.items.select_related('product')
    
    context = {
        'order': order,
        'order_items': order_items,
        'is_buyer': request.user == order.user,
        'is_vendor': request.user == order.vendor.user,
        'can_dispute': order.can_dispute(),
        'can_finalize': order.can_finalize() and request.user == order.user,
        'can_ship': order.status == 'LOCKED' and request.user == order.vendor.user,
    }
    
    return render(request, "orders/detail.html", context)


@login_required
@require_POST
def confirm_receipt(request, pk):
    """Buyer confirms receipt of order"""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    if not order.can_finalize():
        messages.error(request, "This order cannot be finalized")
        return redirect('orders:detail', pk=pk)
    
    try:
        # Release funds from escrow to vendor
        EscrowService.release_funds(order)
        messages.success(request, "Order completed! Funds have been released to the vendor.")
    except Exception as e:
        messages.error(request, f"Failed to release funds: {str(e)}")
    
    return redirect('orders:detail', pk=pk)


@login_required
@require_POST
def mark_shipped(request, pk):
    """Vendor marks order as shipped"""
    order = get_object_or_404(Order, pk=pk, vendor__user=request.user)
    
    if order.status != 'LOCKED':
        messages.error(request, "This order cannot be marked as shipped")
        return redirect('orders:detail', pk=pk)
    
    order.mark_shipped()
    messages.success(request, "Order marked as shipped. Auto-finalization will occur in 14 days if not disputed.")
    
    return redirect('orders:detail', pk=pk)


@login_required
def raise_dispute(request, pk):
    """Raise a dispute for an order"""
    order = get_object_or_404(Order, pk=pk)
    
    # Check if user is involved in the order
    if request.user != order.user and request.user != order.vendor.user:
        messages.error(request, "You cannot dispute this order")
        return redirect('orders:list')
    
    # Check if dispute already exists
    if hasattr(order, 'dispute'):
        messages.info(request, "A dispute already exists for this order")
        return redirect('disputes:detail', pk=order.dispute.id)
    
    if not order.can_dispute():
        messages.error(request, "This order cannot be disputed in its current status")
        return redirect('orders:detail', pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for the dispute")
            return render(request, 'orders/raise_dispute.html', {'order': order})
        
        # Determine complainant and respondent
        if request.user == order.user:
            complainant = order.user
            respondent = order.vendor.user
        else:
            complainant = order.vendor.user
            respondent = order.user
        
        # Create dispute
        dispute = Dispute.objects.create(
            order=order,
            complainant=complainant,
            respondent=respondent,
            reason=reason
        )
        
        # Update order status
        order.mark_disputed()
        
        # Add initial statement based on who raised the dispute
        if request.user == order.user:
            dispute.add_buyer_statement(reason)
        else:
            dispute.add_vendor_statement(reason)
        
        messages.success(request, "Dispute has been raised. An admin will review it soon.")
        return redirect('disputes:detail', pk=dispute.id)
    
    return render(request, 'orders/raise_dispute.html', {'order': order})
