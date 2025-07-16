from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q
from django import forms
from products.models import Product
import hashlib
import secrets
import logging
from datetime import timedelta
from .forms import (
    UserProfileForm, PGPKeyForm, CustomPasswordChangeForm, DeleteAccountForm
)
from .models import User, LoginHistory
from .pgp_service import PGPService
from core.utils.cache import log_event

User = get_user_model()

class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


def home(request):
    featured_products = Product.objects.filter(is_available=True)[:6]
    return render(request, 'home.html', {'featured_products': featured_products})


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if not username or not password:
            messages.error(request, 'Username and password are required')
            return render(request, 'accounts/register.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'accounts/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'accounts/register.html')
        
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password
                )
                log_event('user_registered', {'user_id': str(user.id), 'username': username})
                messages.success(request, 'Registration successful! Please log in.')
                return redirect('accounts:login')
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
    
    return render(request, 'accounts/register.html')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('accounts:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user:
                if user.pgp_login_enabled and user.pgp_public_key:
                    pgp_service = PGPService()
                    
                    import_result = pgp_service.import_public_key(user.pgp_public_key)
                    
                    if not import_result['success']:
                        logger.error(f"Failed to import PGP key for user {username}: {import_result['error']}")
                        messages.error(request, 'PGP key error. Please update your PGP key in settings.')
                        return render(request, 'accounts/login.html', {'form': form})
                    
                    challenge = user.generate_pgp_challenge()
                    challenge_message = f"MARKETPLACE-2FA:{challenge}"
                    
                    encrypt_result = pgp_service.encrypt_message(
                        challenge_message,
                        user.pgp_fingerprint
                    )
                    
                    if not encrypt_result['success']:
                        logger.error(f"Failed to encrypt challenge: {encrypt_result['error']}")
                        messages.error(request, 'Failed to generate PGP challenge. Please try again.')
                        return render(request, 'accounts/login.html', {'form': form})
                    
                    request.session['pgp_2fa_user_id'] = str(user.id)
                    request.session['pgp_2fa_timestamp'] = timezone.now().isoformat()
                    request.session['pgp_2fa_encrypted_challenge'] = encrypt_result['encrypted_message']
                    
                    request.session.save()
                    
                    logger.info(f"Generated encrypted challenge for {username}")
                    
                    return redirect('accounts:pgp_challenge')
                
                else:
                    login(request, user)
                    
                    LoginHistory.objects.create(
                        user=user,
                        ip_hash=hashlib.sha256(
                            request.META.get('REMOTE_ADDR', '').encode()
                        ).hexdigest(),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
                        success=True
                    )
                    
                    messages.success(request, 'Logged in successfully!')
                    return redirect('/')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_event('user_logout', {'user_id': str(request.user.id), 'username': request.user.username})
    logout(request)
    return redirect('/')


@login_required
def profile_view(request):
    user = request.user
    
    try:
        from orders.models import Order
        current_orders = Order.objects.filter(
            buyer=user,
            status__in=['created', 'paid', 'shipped']
        ).count()
        total_orders = Order.objects.filter(buyer=user).count()
    except:
        current_orders = 0
        total_orders = 0
    
    try:
        from disputes.models import Dispute
        active_disputes = Dispute.objects.filter(
            order__buyer=user,
            status='open'
        ).count()
    except:
        active_disputes = 0
    
    login_history = LoginHistory.objects.filter(
        user=user,
        success=True
    )[:5]
    
    try:
        wallet = user.wallet
        btc_balance = wallet.btc_balance
        xmr_balance = wallet.xmr_balance
    except:
        btc_balance = 0
        xmr_balance = 0
    
    feedback_percentage = 0
    if user.total_trades > 0:
        feedback_percentage = (user.positive_feedback_count / user.total_trades) * 100
    
    context = {
        'user': user,
        'trust_level': user.get_trust_level(),
        'current_orders': current_orders,
        'total_orders': total_orders,
        'active_disputes': active_disputes,
        'login_history': login_history,
        'btc_balance': btc_balance,
        'xmr_balance': xmr_balance,
        'feedback_percentage': feedback_percentage,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile(request):
    return redirect('accounts:profile_view')


@login_required
def profile_settings(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile settings updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile_settings.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            LoginHistory.objects.create(
                user=user,
                ip_hash=hashlib.sha256(
                    request.META.get('REMOTE_ADDR', '').encode()
                ).hexdigest(),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
                success=True
            )
            
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def pgp_settings(request):
    if request.method == 'POST':
        form = PGPKeyForm(request.POST)
        if form.is_valid():
            user = request.user
            
            if form.cleaned_data['pgp_public_key']:
                pgp_service = PGPService()
                import_result = pgp_service.import_public_key(form.cleaned_data['pgp_public_key'])
                
                if not import_result['success']:
                    messages.error(request, f'Invalid PGP key: {import_result["error"]}')
                    return render(request, 'accounts/pgp_settings.html', {'form': form})
                
                user.pgp_public_key = form.cleaned_data['pgp_public_key']
                user.pgp_fingerprint = import_result['fingerprint']
            
            user.pgp_login_enabled = form.cleaned_data['enable_pgp_login']
            
            user.save()
            messages.success(request, 'PGP settings updated successfully!')
            return redirect('accounts:profile')
    else:
        form = PGPKeyForm(initial={
            'pgp_public_key': request.user.pgp_public_key,
            'enable_pgp_login': request.user.pgp_login_enabled
        })
    
    return render(request, 'accounts/pgp_settings.html', {'form': form})


@login_required
def delete_account(request):
    if request.method == 'POST':
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data['password']):
                messages.error(request, 'Incorrect password')
                return render(request, 'accounts/delete_account.html', {'form': form})
            
            try:
                from orders.models import Order
                active_orders = Order.objects.filter(
                    buyer=request.user,
                    status__in=['created', 'paid', 'shipped']
                ).exists()
                
                if active_orders:
                    messages.error(request, 'Cannot delete account with active orders')
                    return render(request, 'accounts/delete_account.html', {'form': form})
            except:
                pass
            
            with transaction.atomic():
                user = request.user
                
                log_event('account_deleted', {'user_id': str(user.id), 'username': user.username})
                
                logout(request)
                
                user.delete()
                
                messages.success(request, 'Account deleted successfully')
                return redirect('/')
    else:
        form = DeleteAccountForm()
    
    return render(request, 'accounts/delete_account.html', {'form': form})


@login_required
def login_history_view(request):
    history = LoginHistory.objects.filter(user=request.user).order_by('-login_time')[:5]
    return render(request, 'accounts/login_history.html', {'history': history})


@login_required
def test_pgp_encryption(request):
    """Test PGP encryption for debugging"""
    if not request.user.pgp_public_key:
        messages.error(request, 'No PGP key configured')
        return redirect('accounts:pgp_settings')
    
    pgp_service = PGPService()
    
    import_result = pgp_service.import_public_key(request.user.pgp_public_key)
    if not import_result['success']:
        messages.error(request, f'Failed to import key: {import_result["error"]}')
        return redirect('accounts:pgp_settings')
    
    test_message = "This is a test message from the marketplace.\nTimestamp: " + timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    encrypt_result = pgp_service.encrypt_message(test_message, request.user.pgp_fingerprint)
    
    if encrypt_result['success']:
        return render(request, 'accounts/pgp_test.html', {
            'encrypted_message': encrypt_result['encrypted_message'],
            'original_message': test_message,
            'fingerprint': request.user.pgp_fingerprint
        })
    else:
        messages.error(request, f'Encryption failed: {encrypt_result["error"]}')
        return redirect('accounts:pgp_settings')


def pgp_challenge_view(request):
    """Handle PGP 2FA challenge verification with enhanced session persistence"""
    logger = logging.getLogger(__name__)
    
    logger.debug(f"DEBUG: pgp_challenge_view called with method: {request.method}")
    logger.debug(f"DEBUG: Session keys: {list(request.session.keys())}")
    
    user_id = request.session.get('pgp_2fa_user_id')
    timestamp = request.session.get('pgp_2fa_timestamp')
    encrypted_challenge = request.session.get('pgp_2fa_encrypted_challenge')
    
    logger.debug(f"DEBUG: user_id from session: {user_id}")
    logger.debug(f"DEBUG: timestamp from session: {timestamp}")
    logger.debug(f"DEBUG: encrypted_challenge present: {bool(encrypted_challenge)}")
    
    if not user_id or not timestamp or not encrypted_challenge:
        logger.debug("DEBUG: Missing session data, redirecting to login")
        messages.error(request, 'No pending 2FA authentication')
        return redirect('accounts:login')
    
    from dateutil import parser
    session_time = parser.parse(timestamp)
    if timezone.now() - session_time > timedelta(minutes=15):
        messages.error(request, '2FA session expired. Please login again.')
        request.session.pop('pgp_2fa_user_id', None)
        request.session.pop('pgp_2fa_timestamp', None)
        request.session.pop('pgp_2fa_encrypted_challenge', None)
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Invalid session')
        return redirect('accounts:login')
    
    time_remaining = 15 - int((timezone.now() - session_time).total_seconds() / 60)
    
    if request.method == 'POST':
        decrypted_response = request.POST.get('decrypted_response', '').strip()
        
        if not decrypted_response:
            messages.error(request, 'Please provide the decrypted challenge')
            return render(request, 'accounts/pgp_challenge.html', {
                'username': user.username,
                'encrypted_challenge': encrypted_challenge,
                'challenge_format': 'MARKETPLACE-2FA:XXXXXXXXXXXXX',
                'time_remaining': time_remaining
            })
        
        challenge_code = None
        
        logger.debug(f"DEBUG: Received decrypted_response = {repr(decrypted_response)}")
        logger.debug(f"DEBUG: Current user.pgp_challenge = {repr(user.pgp_challenge)}")
        logger.debug(f"DEBUG: Challenge expires at = {user.pgp_challenge_expires}")
        
        if decrypted_response.startswith('MARKETPLACE-2FA:'):
            challenge_code = decrypted_response.replace('MARKETPLACE-2FA:', '').strip()
        elif len(decrypted_response) >= 32:  # Just the challenge code (allow longer)
            challenge_code = decrypted_response.strip()
        else:
            if 'MARKETPLACE-2FA:' in decrypted_response:
                parts = decrypted_response.split('MARKETPLACE-2FA:')
                if len(parts) > 1:
                    challenge_code = parts[1].strip()
        
        logger.debug(f"DEBUG: Extracted challenge_code = {repr(challenge_code)}")
        
        if challenge_code and user.verify_pgp_challenge(challenge_code):
            login(request, user)
            
            request.session.pop('pgp_2fa_user_id', None)
            request.session.pop('pgp_2fa_timestamp', None)
            request.session.pop('pgp_2fa_encrypted_challenge', None)
            
            LoginHistory.objects.create(
                user=user,
                ip_hash=hashlib.sha256(
                    request.META.get('REMOTE_ADDR', '').encode()
                ).hexdigest(),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
                success=True
            )
            
            messages.success(request, 'PGP authentication successful!')
            return redirect('/')
        else:
            messages.error(request, 'Invalid challenge code. Please try again.')
            logger.warning(f"Invalid PGP challenge attempt for user {user.username}")
        
        return render(request, 'accounts/pgp_challenge.html', {
            'username': user.username,
            'encrypted_challenge': encrypted_challenge,
            'challenge_format': 'MARKETPLACE-2FA:XXXXXXXXXXXXX',
            'time_remaining': time_remaining
        })
    
    return render(request, 'accounts/pgp_challenge.html', {
        'username': user.username,
        'encrypted_challenge': encrypted_challenge,
        'challenge_format': 'MARKETPLACE-2FA:XXXXXXXXXXXXX',
        'time_remaining': time_remaining
    })
