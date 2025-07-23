from django.core.cache import cache
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger('wallet.security')


class WalletSecurityMiddleware:
    """Security middleware for wallet operations"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            self.check_session_timeout(request)
            
            request.session['last_activity'] = timezone.now().timestamp()
        
        response = self.get_response(request)
        
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    def check_session_timeout(self, request):
        """Check for session timeout"""
        last_activity = request.session.get('last_activity')
        if last_activity:
            timeout = getattr(settings, 'WALLET_SESSION_TIMEOUT_MINUTES', 30)
            if timezone.now().timestamp() - last_activity > (timeout * 60):
                from django.contrib.auth import logout
                logout(request)
                messages.info(
                    request, 
                    "Your session has expired due to inactivity."
                )


class RateLimitMiddleware:
    """Rate limiting middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            
            if '/withdraw/' in path and request.method == 'POST':
                if not self.check_rate_limit(request, 'withdraw', 5, 3600):
                    messages.error(request, "Too many withdrawal attempts. Please try again later.")
                    return redirect('wallets:dashboard')
            
            elif '/convert/' in path and request.method == 'POST':
                if not self.check_rate_limit(request, 'convert', 20, 3600):
                    messages.error(request, "Too many conversion attempts. Please try again later.")
                    return redirect('wallets:dashboard')
        
        return self.get_response(request)
    
    def check_rate_limit(self, request, action, max_attempts, window):
        """Check rate limit for specific action"""
        cache_key = f'rate_limit:{request.user.id}:{action}'
        attempts = cache.get(cache_key, 0)
        
        if attempts >= max_attempts:
            logger.warning(f"Rate limit exceeded for user {request.user.username} on {action}")
            return False
        
        cache.set(cache_key, attempts + 1, window)
        return True
