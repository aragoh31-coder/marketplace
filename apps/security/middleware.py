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


class EnhancedSecurityMiddleware:
    """Enhanced security middleware with comprehensive bot detection"""
    
    BOT_USER_AGENTS = [
        r'.*bot.*', r'.*crawler.*', r'.*spider.*', r'.*scraper.*',
        r'curl', r'wget', r'python-requests', r'http', r'test',
        r'automated', r'headless', r'phantom', r'selenium', r'webdriver'
    ]
    
    SUSPICIOUS_PATTERNS = [
        r'/admin', r'/wp-admin', r'\.php$', r'\.asp$',
        r'/config', r'/backup', r'\.sql$', r'\.env$',
        r'/\.git', r'/\.svn', r'/\.htaccess'
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_bot_request(request):
            logger.warning(f"Bot detected: {request.META.get('HTTP_USER_AGENT', '')}")
            return render(request, 'security/captcha_challenge.html', {
                'challenge_question': '2 + 2',
                'challenge_id': 'bot_challenge',
                'timestamp': time.time()
            })
        
        if self._is_suspicious_request(request):
            logger.warning(f"Suspicious request: {request.path}")
            return HttpResponseForbidden("Access denied")
        
        if self._is_rate_limited(request):
            return render(request, 'security/rate_limited.html', {
                'retry_after': 60
            })
        
        response = self.get_response(request)
        
        self._add_security_headers(response)
        
        return response

    def _is_bot_request(self, request):
        """Enhanced bot detection"""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        for pattern in self.BOT_USER_AGENTS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                if any(legit in user_agent for legit in ['googlebot', 'bingbot', 'duckduckbot']):
                    return False
                return True
        
        if not user_agent or len(user_agent) < 10:
            return True
        
        if not request.META.get('HTTP_ACCEPT_LANGUAGE'):
            return True
        
        return False

    def _is_suspicious_request(self, request):
        """Check for suspicious request patterns"""
        path = request.path.lower()
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, path):
                return True
        
        for key, value in request.GET.items():
            if any(sql_keyword in str(value).lower() for sql_keyword in 
                   ['union', 'select', 'drop', 'insert', 'delete', 'update', 'exec']):
                return True
        
        for key, value in request.GET.items():
            if any(xss_pattern in str(value).lower() for xss_pattern in 
                   ['<script', 'javascript:', 'onload=', 'onerror=', 'eval(']):
                return True
        
        return False

    def _is_rate_limited(self, request):
        """Advanced rate limiting"""
        ip_hash = hashlib.sha256(
            self.get_client_ip(request).encode()
        ).hexdigest()
        
        windows = [
            ('1min', 60, 30),    # 30 requests per minute
            ('5min', 300, 100),  # 100 requests per 5 minutes
            ('1hour', 3600, 500) # 500 requests per hour
        ]
        
        for window_name, duration, limit in windows:
            cache_key = f"rate_limit_{window_name}_{ip_hash}"
            request_count = cache.get(cache_key, 0)
            
            if request_count >= limit:
                logger.warning(f"Rate limit exceeded: {window_name} for {ip_hash}")
                return True
            
            cache.set(cache_key, request_count + 1, duration)
        
        return False

    def _add_security_headers(self, response):
        """Add comprehensive security headers"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'none'; object-src 'none'; style-src 'self' 'unsafe-inline';"
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
