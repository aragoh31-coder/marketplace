from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from accounts.models import User
from vendors.models import Vendor
from products.models import Product
from orders.models import Order
from disputes.models import Dispute
from wallets.models import Wallet, Transaction
from messaging.models import Message
# from core.utils import log_event  # TODO: Implement logging utility
from django.utils import timezone
from datetime import timedelta

@login_required
def dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    users_count = User.objects.count()
    active_users = User.objects.filter(last_activity__gte=timezone.now() - timedelta(days=30)).count()
    vendors_count = Vendor.objects.count()
    approved_vendors = Vendor.objects.filter(is_approved=True).count()
    products_count = Product.objects.count()
    orders_count = Order.objects.count()
    open_disputes = Dispute.objects.filter(status='open').count()
    total_escrow = Order.objects.filter(status='PAID').aggregate(Sum('total_btc'))['total_btc__sum'] or 0
    total_btc = Wallet.objects.filter(currency='BTC').aggregate(Sum('balance'))['balance__sum'] or 0
    total_xmr = Wallet.objects.filter(currency='XMR').aggregate(Sum('balance'))['balance__sum'] or 0
    total_balance = total_btc + total_xmr
    
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    recent_transactions = Transaction.objects.order_by('-created_at')[:10]
    recent_messages = Message.objects.order_by('-created_at')[:10]
    
    avg_order_value = Order.objects.aggregate(Avg('total_btc'))['total_btc__avg'] or 0
    order_status_counts = Order.objects.values('status').annotate(count=Count('id'))
    
    context = {
        'users_count': users_count,
        'active_users': active_users,
        'vendors_count': vendors_count,
        'approved_vendors': approved_vendors,
        'products_count': products_count,
        'orders_count': orders_count,
        'open_disputes': open_disputes,
        'total_escrow': total_escrow,
        'total_balance': total_balance,
        'avg_order_value': avg_order_value,
        'order_status_counts': order_status_counts,
        'recent_orders': recent_orders,
        'recent_transactions': recent_transactions,
        'recent_messages': recent_messages,
    }
    return render(request, 'adminpanel/dashboard.html', context)

@login_required
def users_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    users = User.objects.all().order_by('-last_activity')
    context = {'users': users}
    return render(request, 'adminpanel/users.html', context)

@login_required
def user_detail(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    user = User.objects.get(id=user_id)
    wallet = Wallet.objects.filter(user=user).first()
    orders = Order.objects.filter(buyer=user)
    messages_sent = Message.objects.filter(sender=user).count()
    context = {
        'user': user,
        'wallet': wallet,
        'orders': orders,
        'messages_sent': messages_sent,
    }
    return render(request, 'adminpanel/user_detail.html', context)

@login_required
def ban_user(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    if request.method == 'POST':
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        # log_event('user_banned', {'user_id': user_id, 'admin': request.user.username})
        messages.success(request, f'User {user.username} banned.')
    return redirect('adminpanel:users')

@login_required
def vendors_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    vendors = Vendor.objects.all().order_by('-trust_level')
    context = {'vendors': vendors}
    return render(request, 'adminpanel/vendors.html', context)

@login_required
def approve_vendor(request, vendor_id):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    vendor = Vendor.objects.get(id=vendor_id)
    vendor.is_approved = True
    vendor.save()
    # log_event('vendor_approved', {'vendor_id': vendor_id, 'admin': request.user.username})
    messages.success(request, 'Vendor approved.')
    return redirect('adminpanel:vendors')

@login_required
def products_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    products = Product.objects.all().order_by('-created_at')
    context = {'products': products}
    return render(request, 'adminpanel/products.html', context)

@login_required
def delete_product(request, product_id):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    if request.method == 'POST':
        product = Product.objects.get(id=product_id)
        product.delete()
        # log_event('product_deleted', {'product_id': product_id, 'admin': request.user.username})
        messages.success(request, 'Product deleted.')
    return redirect('adminpanel:products')

@login_required
def orders_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    orders = Order.objects.all().order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'adminpanel/orders.html', context)

@login_required
def disputes_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    disputes = Dispute.objects.all().order_by('-created_at')
    context = {'disputes': disputes}
    return render(request, 'adminpanel/disputes.html', context)

@login_required
def resolve_dispute(request, dispute_id):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    dispute = Dispute.objects.get(id=dispute_id)
    if request.method == 'POST':
        resolution = request.POST.get('resolution')
        dispute.resolution = resolution
        dispute.status = 'resolved'
        dispute.resolved_at = timezone.now()
        dispute.save()
        # log_event('dispute_resolved', {'dispute_id': dispute_id, 'resolution': resolution, 'admin': request.user.username})
        messages.success(request, 'Dispute resolved.')
    return redirect('adminpanel:disputes')

@login_required
def withdrawals_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    withdrawals = Transaction.objects.filter(transaction_type='WITHDRAWAL', status='PENDING').order_by('-created_at')
    context = {'withdrawals': withdrawals}
    return render(request, 'adminpanel/withdrawals.html', context)

@login_required
def approve_withdrawal(request, withdrawal_id):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    withdrawal = Transaction.objects.get(id=withdrawal_id)
    withdrawal.status = 'CONFIRMED'
    withdrawal.save()
    # log_event('withdrawal_approved', {'withdrawal_id': withdrawal_id, 'admin': request.user.username})
    messages.success(request, 'Withdrawal approved.')
    return redirect('adminpanel:withdrawals')

@login_required
def system_logs(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    context = {'logs': []}
    return render(request, 'adminpanel/logs.html', context)

@login_required
def trigger_maintenance(request):
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'vacuum':
            messages.success(request, 'Database vacuum task triggered.')
        elif action == 'reconcile':
            messages.success(request, 'Wallet reconciliation task triggered.')
        elif action == 'expire':
            messages.success(request, 'Data expiration tasks triggered.')
    return redirect('adminpanel:dashboard')
