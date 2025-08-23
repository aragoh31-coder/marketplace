"""
Views using One-Click CAPTCHA for authentication
"""
import logging
import hashlib

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView
from django.http import HttpResponseRedirect

from apps.security.forms_oneclick import SecureLoginFormOneClick, SecureRegistrationFormOneClick
from apps.security.models import log_security_event
from accounts.models import LoginHistory

logger = logging.getLogger(__name__)


@csrf_protect
@never_cache
def login_view_oneclick(request):
    """Login view with One-Click CAPTCHA"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = SecureLoginFormOneClick(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            user = authenticate(request, username=username, password=password)
            
            if user:
                # Log successful login
                session_id = request.session.session_key or 'no-session'
                
                LoginHistory.objects.create(
                    user=user,
                    ip_hash=hashlib.sha256(session_id.encode()).hexdigest(),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    success=True
                )
                
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect to next URL or home
                next_url = request.GET.get('next', 'core:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            # Form validation failed
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
    else:
        form = SecureLoginFormOneClick(request=request)
    
    return render(request, 'accounts/login_oneclick.html', {
        'form': form,
        'title': 'Login'
    })


@csrf_protect
@never_cache
def register_view_oneclick(request):
    """Registration view with One-Click CAPTCHA"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = SecureRegistrationFormOneClick(data=request.POST, request=request)
        if form.is_valid():
            user = form.save()
            
            # Log registration
            session_id = request.session.session_key or 'no-session'
            log_security_event(
                user,
                'registration',
                {
                    'session_id': session_id,
                    'timestamp': timezone.now()
                }
            )
            
            messages.success(
                request, 
                'Registration successful! Please login with your credentials.'
            )
            return redirect('accounts:login')
        else:
            # Form validation failed
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
    else:
        form = SecureRegistrationFormOneClick(request=request)
    
    return render(request, 'accounts/register_oneclick.html', {
        'form': form,
        'title': 'Register'
    })


@method_decorator([csrf_protect, never_cache], name='dispatch')
class SecureLoginViewOneClick(FormView):
    """Class-based login view with One-Click CAPTCHA"""
    template_name = 'accounts/login_oneclick.html'
    form_class = SecureLoginFormOneClick
    success_url = reverse_lazy('core:home')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        
        user = authenticate(self.request, username=username, password=password)
        
        if user:
            login(self.request, user)
            messages.success(self.request, f'Welcome back, {user.username}!')
            return super().form_valid(form)
        else:
            messages.error(self.request, 'Invalid username or password.')
            return self.form_invalid(form)
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()


@method_decorator([csrf_protect, never_cache], name='dispatch')
class SecureRegistrationViewOneClick(FormView):
    """Class-based registration view with One-Click CAPTCHA"""
    template_name = 'accounts/register_oneclick.html'
    form_class = SecureRegistrationFormOneClick
    success_url = reverse_lazy('accounts:login')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        user = form.save()
        messages.success(
            self.request,
            'Registration successful! Please login with your credentials.'
        )
        return super().form_valid(form)