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
from .forms import (
    UserProfileForm, PGPKeyForm, CustomPasswordChangeForm, DeleteAccountForm
)
from .models import User, LoginHistory
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
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            if user:
                if user.pgp_login_enabled and user.pgp_public_key:
                    request.session['pgp_challenge_user'] = str(user.id)
                    return redirect('accounts:pgp_challenge')
                
                login(request, user)
                user.last_activity = timezone.now()
                user.failed_login_attempts = 0
                user.save()
                
                LoginHistory.objects.create(
                    user=user,
                    ip_hash=hashlib.sha256(
                        request.META.get('REMOTE_ADDR', '').encode()
                    ).hexdigest(),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
                    success=True
                )
                
                log_event('user_login', {'user_id': str(user.id), 'username': username})
                request.session.cycle_key()
                return redirect('/')
            else:
                try:
                    user = User.objects.get(username=username)
                    user.failed_login_attempts += 1
                    user.save()
                    
                    LoginHistory.objects.create(
                        user=user,
                        ip_hash=hashlib.sha256(
                            request.META.get('REMOTE_ADDR', '').encode()
                        ).hexdigest(),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
                        success=False
                    )
                except User.DoesNotExist:
                    pass
                
                messages.error(request, 'Invalid username or password')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_event('user_logout', {'user_id': str(request.user.id), 'username': request.user.username})
    logout(request)
    return redirect('home')


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
                user.pgp_public_key = form.cleaned_data['pgp_public_key']
                user.pgp_fingerprint = form.fingerprint
            
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
                return redirect('home')
    else:
        form = DeleteAccountForm()
    
    return render(request, 'accounts/delete_account.html', {'form': form})


@login_required
def login_history_view(request):
    history = LoginHistory.objects.filter(user=request.user)[:20]
    return render(request, 'accounts/login_history.html', {'history': history})


def pgp_challenge_view(request):
    user_id = request.session.get('pgp_challenge_user')
    if not user_id:
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('accounts:login')
    
    if request.method == 'POST':
        login(request, user)
        del request.session['pgp_challenge_user']
        
        LoginHistory.objects.create(
            user=user,
            ip_hash=hashlib.sha256(
                request.META.get('REMOTE_ADDR', '').encode()
            ).hexdigest(),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
            success=True
        )
        
        return redirect('home')
    
    challenge = secrets.token_urlsafe(32)
    
    return render(request, 'accounts/pgp_challenge.html', {
        'challenge': challenge,
        'user': user
    })
