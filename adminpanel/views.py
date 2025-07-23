from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import secrets
import json
from accounts.models import User
from vendors.models import Vendor
from products.models import Product
from orders.models import Order
from disputes.models import Dispute
from wallets.models import Wallet, Transaction
from messaging.models import Message
from .models import AdminLog
from .forms import SecondaryAuthForm, AdminPGPChallengeForm, AdminLoginForm
from django.conf import settings

def admin_login(request):
    """Enhanced admin login with triple authentication"""
    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            if user and user.is_superuser:
                failed_attempts = request.session.get(f'admin_failed_attempts_{username}', 0)
                lockout_time = request.session.get(f'admin_lockout_time_{username}')
                
                if lockout_time and timezone.now().timestamp() < lockout_time:
                    messages.error(request, 'Account temporarily locked due to failed attempts.')
                    return render(request, 'adminpanel/locked.html')
                
                request.session.pop(f'admin_failed_attempts_{username}', None)
                request.session.pop(f'admin_lockout_time_{username}', None)
                
                request.session['admin_pending_user_id'] = str(user.id)
                request.session['admin_login_timestamp'] = timezone.now().timestamp()
                
                AdminLog.objects.create(
                    admin_user=user,
                    action_type='LOGIN',
                    target_model='User',
                    target_id=str(user.id),
                    description=f'First authentication step completed for {username}',
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
                )
                
                return redirect('adminpanel:secondary_auth')
            else:
                failed_attempts = request.session.get(f'admin_failed_attempts_{username}', 0) + 1
                request.session[f'admin_failed_attempts_{username}'] = failed_attempts
                
                if failed_attempts >= settings.ADMIN_PANEL_CONFIG['MAX_FAILED_ATTEMPTS']:
                    lockout_time = timezone.now().timestamp() + settings.ADMIN_PANEL_CONFIG['LOCKOUT_DURATION']
                    request.session[f'admin_lockout_time_{username}'] = lockout_time
                    messages.error(request, 'Too many failed attempts. Account locked.')
                    return render(request, 'adminpanel/locked.html')
                
                messages.error(request, 'Invalid credentials or insufficient permissions.')
    else:
        form = AdminLoginForm()
    
    return render(request, 'adminpanel/login.html', {'form': form})


def secondary_auth(request):
    """Secondary password authentication"""
    pending_user_id = request.session.get('admin_pending_user_id')
    if not pending_user_id:
        return redirect('adminpanel:login')
    
    if request.method == 'POST':
        form = SecondaryAuthForm(request.POST)
        if form.is_valid():
            secondary_password = form.cleaned_data['password']
            
            if secondary_password == settings.ADMIN_PANEL_CONFIG['SECONDARY_PASSWORD']:
                user = User.objects.get(id=pending_user_id)
                
                if settings.ADMIN_PGP_CONFIG['ENFORCE_PGP'] and user.pgp_public_key:
                    return redirect('adminpanel:pgp_verify')
                else:
                    login(request, user)
                    request.session.pop('admin_pending_user_id', None)
                    request.session.pop('admin_login_timestamp', None)
                    
                    request.session.set_expiry(settings.ADMIN_PANEL_CONFIG['SESSION_TIMEOUT'])
                    
                    AdminLog.objects.create(
                        admin_user=user,
                        action_type='LOGIN',
                        target_model='User',
                        target_id=str(user.id),
                        description=f'Admin login completed for {user.username}',
                        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
                    )
                    
                    messages.success(request, 'Welcome to the admin panel!')
                    return redirect('adminpanel:dashboard')
            else:
                messages.error(request, 'Invalid secondary password.')
    else:
        form = SecondaryAuthForm()
    
    return render(request, 'adminpanel/secondary_auth.html', {'form': form})


def pgp_verify(request):
    """PGP challenge verification for admin access"""
    pending_user_id = request.session.get('admin_pending_user_id')
    if not pending_user_id:
        return redirect('adminpanel:login')
    
    user = User.objects.get(id=pending_user_id)
    
    if request.method == 'POST':
        form = AdminPGPChallengeForm(request.POST)
        if form.is_valid():
            signed_response = form.cleaned_data['signed_challenge']
            challenge = request.session.get('admin_pgp_challenge')
            
            if challenge:
                from accounts.pgp_service import PGPService
                pgp_service = PGPService()
                
                verify_result = pgp_service.verify_signature(signed_response, challenge)
                
                if verify_result['success']:
                    login(request, user)
                    request.session.pop('admin_pending_user_id', None)
                    request.session.pop('admin_login_timestamp', None)
                    request.session.pop('admin_pgp_challenge', None)
                    
                    request.session.set_expiry(settings.ADMIN_PANEL_CONFIG['SESSION_TIMEOUT'])
                    
                    AdminLog.objects.create(
                        admin_user=user,
                        action_type='LOGIN',
                        target_model='User',
                        target_id=str(user.id),
                        description=f'Admin login with PGP verification completed for {user.username}',
                        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
                    )
                    
                    messages.success(request, 'Welcome to the admin panel!')
                    return redirect('adminpanel:dashboard')
                else:
                    messages.error(request, 'Invalid PGP signature.')
            else:
                messages.error(request, 'PGP challenge expired.')
    else:
        form = AdminPGPChallengeForm()
        
        from accounts.pgp_service import PGPService
        pgp_service = PGPService()
        
        challenge = f"Admin login challenge for {user.username} at {timezone.now().isoformat()}"
        request.session['admin_pgp_challenge'] = challenge
        
        encrypt_result = pgp_service.encrypt_message(challenge, user.pgp_fingerprint)
        
        if not encrypt_result['success']:
            messages.error(request, 'Failed to generate PGP challenge.')
            return redirect('adminpanel:login')
    
    return render(request, 'adminpanel/pgp_verify.html', {
        'form': form,
        'user': user,
        'encrypted_challenge': encrypt_result.get('encrypted_message', '') if 'encrypt_result' in locals() else ''
    })
    
    challenge = request.session.get('admin_pgp_challenge', '')
    return render(request, 'adminpanel/pgp_verify.html', {
        'form': form,
        'challenge': challenge,
        'user': user
    })


def locked_account(request):
    """Display account lockout page"""
    return render(request, 'adminpanel/locked.html')


def admin_logout(request):
    """Admin logout"""
    if request.user.is_authenticated:
        AdminLog.objects.create(
            user=request.user,
            action='LOGOUT',
            details=f'Admin logout for {request.user.username}'
        )
    
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('adminpanel:login')


@login_required
def admin_dashboard(request):
    """Enhanced admin dashboard with comprehensive metrics"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('adminpanel:login')
    
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_today = User.objects.filter(date_joined__date=timezone.now().date()).count()
    new_users_week = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count()
    
    total_vendors = Vendor.objects.count()
    approved_vendors = Vendor.objects.filter(is_approved=True).count()
    pending_vendors = Vendor.objects.filter(is_approved=False).count()
    
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    orders_today = Order.objects.filter(created_at__date=timezone.now().date()).count()
    
    total_disputes = Dispute.objects.count()
    open_disputes = Dispute.objects.filter(status='OPEN').count()
    resolved_disputes = Dispute.objects.filter(status='RESOLVED').count()
    
    try:
        btc_revenue = Transaction.objects.filter(
            transaction_type='DEPOSIT',
            currency='BTC'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        xmr_revenue = Transaction.objects.filter(
            transaction_type='DEPOSIT',
            currency='XMR'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        btc_revenue_month = Transaction.objects.filter(
            transaction_type='DEPOSIT',
            currency='BTC',
            created_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        xmr_revenue_month = Transaction.objects.filter(
            transaction_type='DEPOSIT',
            currency='XMR',
            created_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
    except Exception:
        btc_revenue = xmr_revenue = btc_revenue_month = xmr_revenue_month = 0
    
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_orders = Order.objects.order_by('-created_at')[:5]
    recent_disputes = Dispute.objects.order_by('-created_at')[:3]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'total_vendors': total_vendors,
        'approved_vendors': approved_vendors,
        'pending_vendors': pending_vendors,
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
        'orders_today': orders_today,
        'total_disputes': total_disputes,
        'open_disputes': open_disputes,
        'resolved_disputes': resolved_disputes,
        'btc_revenue': btc_revenue,
        'xmr_revenue': xmr_revenue,
        'btc_revenue_month': btc_revenue_month,
        'xmr_revenue_month': xmr_revenue_month,
        'recent_users': recent_users,
        'recent_orders': recent_orders,
        'recent_disputes': recent_disputes,
    }
    return render(request, 'adminpanel/dashboard.html', context)


dashboard = admin_dashboard

@login_required
def admin_users(request):
    """Enhanced user listing with search and filters"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('adminpanel:login')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    vendor_filter = request.GET.get('vendor', '')
    
    users = User.objects.all()
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'staff':
        users = users.filter(is_staff=True)
    
    if vendor_filter == 'vendors':
        users = users.filter(vendor__isnull=False)
    elif vendor_filter == 'non_vendors':
        users = users.filter(vendor__isnull=True)
    
    users = users.order_by('-date_joined')
    
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'vendor_filter': vendor_filter,
        'total_users': users.count(),
    }
    return render(request, 'adminpanel/users.html', context)


users_list = admin_users

@login_required
def admin_user_detail(request, username):
    """Comprehensive user details view with financial data"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('adminpanel:login')
    
    user = get_object_or_404(User, username=username)
    
    try:
        wallet = user.wallet
        btc_balance = wallet.balance_btc
        xmr_balance = wallet.balance_xmr
        btc_escrow = wallet.escrow_btc
        xmr_escrow = wallet.escrow_xmr
    except:
        wallet = None
        btc_balance = xmr_balance = btc_escrow = xmr_escrow = 0
    
    transactions = []
    total_deposits_btc = total_deposits_xmr = 0
    total_withdrawals_btc = total_withdrawals_xmr = 0
    
    if wallet:
        transactions = wallet.transactions.order_by('-created_at')[:20]
        
        deposits_btc = wallet.transactions.filter(
            transaction_type='DEPOSIT', currency='BTC'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        deposits_xmr = wallet.transactions.filter(
            transaction_type='DEPOSIT', currency='XMR'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        withdrawals_btc = wallet.transactions.filter(
            transaction_type='WITHDRAWAL', currency='BTC'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        withdrawals_xmr = wallet.transactions.filter(
            transaction_type='WITHDRAWAL', currency='XMR'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_deposits_btc = deposits_btc
        total_deposits_xmr = deposits_xmr
        total_withdrawals_btc = withdrawals_btc
        total_withdrawals_xmr = withdrawals_xmr
    
    orders = user.orders.order_by('-created_at')[:10]
    total_orders = user.orders.count()
    completed_orders = user.orders.filter(status='COMPLETED').count()
    
    buyer_disputes = user.filed_disputes.order_by('-created_at')[:5]
    vendor_disputes = user.received_disputes.order_by('-created_at')[:5]
    total_disputes = buyer_disputes.count() + vendor_disputes.count()
    
    vendor_info = None
    vendor_stats = {}
    if hasattr(user, 'vendor'):
        vendor_info = user.vendor
        from products.models import Product
        vendor_products = Product.objects.filter(vendor=vendor_info)
        vendor_orders = Order.objects.filter(items__product__in=vendor_products).distinct()
        
        vendor_stats = {
            'total_products': vendor_info.products.count(),
            'active_products': vendor_info.products.filter(is_active=True).count(),
            'total_sales': vendor_orders.filter(status='COMPLETED').count(),
            'pending_orders': vendor_orders.filter(status='PENDING').count(),
            'vendor_rating': vendor_info.rating,
            'is_approved': vendor_info.is_approved,
            'vacation_mode': getattr(vendor_info, 'vacation_mode', False),
        }
    
    security_info = {
        'pgp_enabled': bool(user.pgp_public_key),
        'pgp_fingerprint': user.pgp_fingerprint,
        'two_factor_enabled': user.pgp_login_enabled,
        'last_login': user.last_login,
        'date_joined': user.date_joined,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    }
    
    context = {
        'user': user,
        'wallet': wallet,
        'btc_balance': btc_balance,
        'xmr_balance': xmr_balance,
        'btc_escrow': btc_escrow,
        'xmr_escrow': xmr_escrow,
        'transactions': transactions,
        'total_deposits_btc': total_deposits_btc,
        'total_deposits_xmr': total_deposits_xmr,
        'total_withdrawals_btc': total_withdrawals_btc,
        'total_withdrawals_xmr': total_withdrawals_xmr,
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'buyer_disputes': buyer_disputes,
        'vendor_disputes': vendor_disputes,
        'total_disputes': total_disputes,
        'vendor_info': vendor_info,
        'vendor_stats': vendor_stats,
        'security_info': security_info,
    }
    return render(request, 'adminpanel/user_detail.html', context)


user_detail = admin_user_detail

@login_required
def admin_user_action(request, username):
    """Handle various user management actions"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('adminpanel:login')
    
    user = get_object_or_404(User, username=username)
    action = request.POST.get('action')
    
    if request.method == 'POST':
        if action == 'ban':
            user.is_active = False
            user.save()
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE',
                target_model='User',
                target_id=str(user.id),
                description=f'Banned user {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            messages.success(request, f'User {user.username} has been banned.')
            
        elif action == 'unban':
            user.is_active = True
            user.save()
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE',
                target_model='User',
                target_id=str(user.id),
                description=f'Unbanned user {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            messages.success(request, f'User {user.username} has been unbanned.')
            
        elif action == 'reset_2fa':
            user.pgp_public_key = ''
            user.pgp_fingerprint = ''
            user.pgp_login_enabled = False
            user.save()
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE',
                target_model='User',
                target_id=str(user.id),
                description=f'Reset 2FA for user {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            messages.success(request, f'2FA has been reset for {user.username}.')
            
        elif action == 'make_staff':
            user.is_staff = True
            user.save()
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE',
                target_model='User',
                target_id=str(user.id),
                description=f'Granted staff privileges to {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            messages.success(request, f'{user.username} is now a staff member.')
            
        elif action == 'remove_staff':
            user.is_staff = False
            user.save()
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE',
                target_model='User',
                target_id=str(user.id),
                description=f'Removed staff privileges from {user.username}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            messages.success(request, f'Staff privileges removed from {user.username}.')
    
    return redirect('adminpanel:user_detail', username=username)


ban_user = admin_user_action

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
def admin_withdrawal_detail(request, withdrawal_id):
    """Detailed view of withdrawal request for admin processing"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('adminpanel:login')
    
    from wallets.models import WithdrawalRequest
    withdrawal = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'approve':
            withdrawal.status = 'approved'
            withdrawal.processed_by = request.user
            withdrawal.processed_at = timezone.now()
            withdrawal.admin_notes = admin_notes
            withdrawal.save()
            
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE',
                target_model='WithdrawalRequest',
                target_id=str(withdrawal.id),
                description=f'Approved withdrawal #{withdrawal.id} for {withdrawal.amount} {withdrawal.currency}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Withdrawal #{withdrawal.id} approved successfully.')
            
        elif action == 'reject':
            withdrawal.status = 'rejected'
            withdrawal.processed_by = request.user
            withdrawal.processed_at = timezone.now()
            withdrawal.admin_notes = admin_notes
            withdrawal.save()
            
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='UPDATE',
                target_model='WithdrawalRequest',
                target_id=str(withdrawal.id),
                description=f'Rejected withdrawal #{withdrawal.id} for {withdrawal.amount} {withdrawal.currency}',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
            )
            
            messages.success(request, f'Withdrawal #{withdrawal.id} rejected.')
        
        return redirect('adminpanel:withdrawal_detail', withdrawal_id=withdrawal.id)
    
    context = {
        'withdrawal': withdrawal,
        'user': withdrawal.user,
    }
    return render(request, 'adminpanel/withdrawal_detail.html', context)


@login_required
def admin_security_logs(request):
    """View security audit logs"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('adminpanel:login')
    
    from wallets.models import AuditLog
    
    flagged_logs = AuditLog.objects.filter(flagged=True).order_by('-created_at')[:50]
    
    high_risk_logs = AuditLog.objects.filter(
        risk_score__gte=60
    ).order_by('-created_at')[:50]
    
    context = {
        'flagged_logs': flagged_logs,
        'high_risk_logs': high_risk_logs,
    }
    return render(request, 'adminpanel/security_logs.html', context)


@login_required
def admin_wallet_overview(request):
    """Comprehensive wallet system overview"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('adminpanel:login')
    
    from wallets.models import Wallet, WithdrawalRequest, Transaction, WalletBalanceCheck
    from django.db.models import Sum, Count
    
    total_wallets = Wallet.objects.count()
    total_btc = Wallet.objects.aggregate(Sum('balance_btc'))['balance_btc__sum'] or 0
    total_xmr = Wallet.objects.aggregate(Sum('balance_xmr'))['balance_xmr__sum'] or 0
    total_escrow_btc = Wallet.objects.aggregate(Sum('escrow_btc'))['escrow_btc__sum'] or 0
    total_escrow_xmr = Wallet.objects.aggregate(Sum('escrow_xmr'))['escrow_xmr__sum'] or 0
    
    pending_withdrawals = WithdrawalRequest.objects.filter(status='pending').count()
    reviewing_withdrawals = WithdrawalRequest.objects.filter(status='reviewing').count()
    high_risk_withdrawals = WithdrawalRequest.objects.filter(
        status__in=['pending', 'reviewing'],
        risk_score__gte=60
    ).count()
    
    recent_discrepancies = WalletBalanceCheck.objects.filter(
        discrepancy_found=True,
        resolved=False
    ).order_by('-checked_at')[:10]
    
    recent_transactions = Transaction.objects.order_by('-created_at')[:20]
    
    context = {
        'total_wallets': total_wallets,
        'total_btc': total_btc,
        'total_xmr': total_xmr,
        'total_escrow_btc': total_escrow_btc,
        'total_escrow_xmr': total_escrow_xmr,
        'pending_withdrawals': pending_withdrawals,
        'reviewing_withdrawals': reviewing_withdrawals,
        'high_risk_withdrawals': high_risk_withdrawals,
        'recent_discrepancies': recent_discrepancies,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'adminpanel/wallet_overview.html', context)


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

@login_required
def image_settings(request):
    """Image upload configuration page"""
    if not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect('accounts:home')
    
    from django.conf import settings
    
    if request.method == 'POST':
        storage_backend = request.POST.get('storage_backend', 'local')
        jpeg_quality = int(request.POST.get('jpeg_quality', 85))
        thumbnail_quality = int(request.POST.get('thumbnail_quality', 75))
        uploads_per_hour = int(request.POST.get('uploads_per_hour', 10))
        uploads_per_day = int(request.POST.get('uploads_per_day', 50))
        
        if not 50 <= jpeg_quality <= 95:
            jpeg_quality = 85
        if not 50 <= thumbnail_quality <= 85:
            thumbnail_quality = 75
        
        messages.success(request, 'Image settings updated successfully!')
        return redirect('adminpanel:image_settings')
    
    config = getattr(settings, 'IMAGE_UPLOAD_SETTINGS', {})
    
    context = {
        'current_backend': config.get('STORAGE_BACKEND', 'local'),
        'max_file_size_mb': 2,  # Fixed at 2MB
        'uploads_per_hour': config.get('UPLOADS_PER_HOUR', 10),
        'uploads_per_day': config.get('UPLOADS_PER_DAY', 50),
        'allowed_extensions': config.get('ALLOWED_EXTENSIONS', ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']),
        'max_dimensions': config.get('MAX_IMAGE_DIMENSIONS', (1920, 1080)),
        'thumbnail_size': config.get('THUMBNAIL_SIZE', (400, 400)),
        'current_settings': config,
    }
    
    return render(request, 'adminpanel/image_settings.html', context)
