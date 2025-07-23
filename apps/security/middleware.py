from django.core.cache import cache
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import render
import logging
import hashlib
import re
import time
from datetime import timedelta

logger = logging.getLogger('wallet.security')


class WalletSecurityMiddleware:
    """Security middleware for wallet operations"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            if settings.WALLET_SECURITY.get('REQUIRE_IP_MATCH'):
                self.check_ip_consistency(request)
            
            self.check_session_timeout(request)
            
            request.session['last_activity'] = timezone.now().timestamp()
        
        response = self.get_response(request)
        
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    def check_ip_consistency(self, request):
        """Ensure user's IP hasn't changed during session"""
        current_ip = self.get_client_ip(request)
        session_ip = request.session.get('ip_address')
        
        if session_ip and session_ip != current_ip:
            logger.warning(
                f"IP address change detected for user {request.user.username}: "
                f"{session_ip} -> {current_ip}"
            )
            
            from wallets.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='security_alert',
                ip_address=current_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'alert_type': 'ip_change',
                    'previous_ip': session_ip,
                    'new_ip': current_ip
                },
                flagged=True,
                risk_score=50
            )
            
            from django.contrib.auth import logout
            logout(request)
            messages.warning(
                request, 
                "Your session has been terminated due to IP address change. "
                "Please log in again."
            )
            
        if not session_ip:
            request.session['ip_address'] = current_ip
    
    def check_session_timeout(self, request):
        """Check for session timeout"""
        last_activity = request.session.get('last_activity')
        if last_activity:
            timeout = settings.WALLET_SECURITY.get('SESSION_TIMEOUT_MINUTES', 30)
            if timezone.now().timestamp() - last_activity > (timeout * 60):
                from django.contrib.auth import logout
                logout(request)
                messages.info(
                    request, 
                    "Your session has expired due to inactivity."
                )
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitMiddleware:
    """Rate limiting middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            
            if '/withdraw/' in path:
                if not self.check_rate_limit(
                    request, 
                    'withdraw',
                    settings.WALLET_SECURITY.get('WITHDRAWAL_RATE_LIMIT', 5)
                ):
                    messages.error(
                        request,
                        "Too many withdrawal attempts. Please try again later."
                    )
                    return redirect('wallets:dashboard')
            
            elif '/convert/' in path:
                if not self.check_rate_limit(
                    request,
                    'convert',
                    settings.WALLET_SECURITY.get('CONVERSION_RATE_LIMIT', 20)
                ):
                    messages.error(
                        request,
                        "Too many conversion attempts. Please try again later."
                    )
                    return redirect('wallets:dashboard')
        
        response = self.get_response(request)
        return response
    
    def check_rate_limit(self, request, action, max_attempts):
        """Check rate limit for specific action"""
        ip = self.get_client_ip(request)
        cache_key = f'rate_limit:{action}:{ip}:{request.user.id}'
        
        attempts = cache.get(cache_key, 0)
        if attempts >= max_attempts:
            logger.warning(
                f"Rate limit exceeded for {action} by user {request.user.username} "
                f"from IP {ip}"
            )
            return False
        
        cache.set(cache_key, attempts + 1, 3600)
        return True
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityMiddleware:
    """Additional security middleware"""
    
    BOT_USER_AGENTS = [
        r'.*bot.*', r'.*crawler.*', r'.*spider.*', r'.*scraper.*',
        r'curl', r'wget', r'python-requests', r'http', r'test'
    ]
    
    SUSPICIOUS_PATTERNS = [
        r'/admin', r'/wp-admin', r'\.php$', r'\.asp$',
        r'/config', r'/backup', r'\.sql$'
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        for pattern in self.BOT_USER_AGENTS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                if not any(legit in user_agent for legit in ['googlebot', 'bingbot', 'duckduckbot']):
                    return HttpResponseForbidden("Access denied")
        
        path = request.path.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, path):
                return HttpResponseForbidden("Access denied")
        
        ip = self.get_client_ip(request)
        if self._is_rate_limited(request, ip):
            return HttpResponseForbidden("Rate limit exceeded")
        
        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _is_rate_limited(self, request, ip):
        """Simple rate limiting check"""
        if hasattr(request, 'session'):
            current_time = time.time()
            key = f"requests_{ip}"
            
            requests = request.session.get(key, [])
            requests = [ts for ts in requests if current_time - ts < 60]
            
            if len(requests) >= 60:
                return True
            
            requests.append(current_time)
            request.session[key] = requests
        
        return False
