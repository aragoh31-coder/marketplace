"""
Tor Security Middleware
Enforces security policies for Tor hosting.
"""

import re
from django.http import HttpResponseForbidden
from django.conf import settings


class TorSecurityMiddleware:
    """Middleware to enforce Tor-specific security policies."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Blocked user agents (bots, scrapers, etc.)
        self.blocked_user_agents = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'python-requests', 'scrapy', 'selenium', 'phantomjs'
        ]
        
        # Blocked referrers (external sites)
        self.blocked_referrers = [
            'google.com', 'facebook.com', 'twitter.com', 'youtube.com',
            'amazon.com', 'microsoft.com', 'apple.com'
        ]
    
    def __call__(self, request):
        # Check user agent
        if not self._is_safe_user_agent(request):
            return HttpResponseForbidden("Access denied: Suspicious user agent")
        
        # Check referrer
        if not self._is_safe_referrer(request):
            return HttpResponseForbidden("Access denied: Invalid referrer")
        
        # Add security headers
        response = self.get_response(request)
        self._add_security_headers(response)
        
        return response
    
    def _is_safe_user_agent(self, request):
        """Check if request comes from a safe user agent."""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        # Allow testing tools for development
        testing_tools = [
            'curl', 'python-requests', 'test', 'debug'
        ]
        
        for tool in testing_tools:
            if tool in user_agent:
                return True
        
        # Block known bot user agents
        for blocked in self.blocked_user_agents:
            if blocked in user_agent:
                return False
        
        # Allow legitimate browsers
        safe_browsers = ['firefox', 'chrome', 'safari', 'edge', 'tor']
        if any(browser in user_agent for browser in safe_browsers):
            return True
        
        return True  # Default allow for development
    
    def _is_safe_referrer(self, request):
        """Check if referrer is safe (no external sites)."""
        referrer = request.META.get('HTTP_REFERER', '')
        
        if not referrer:
            return True  # No referrer is safe
        
        # Block external referrers
        for blocked in self.blocked_referrers:
            if blocked in referrer:
                return False
        
        return True
    
    def _add_security_headers(self, response):
        """Add security headers to response."""
        # Basic security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'no-referrer'
        
        # Content Security Policy - Strict for Tor
        csp_parts = []
        csp_parts.append("default-src 'self'")
        csp_parts.append("style-src 'self' 'unsafe-inline'")
        csp_parts.append("script-src 'none'")  # No JavaScript
        csp_parts.append("img-src 'self' data:")
        csp_parts.append("font-src 'self'")
        csp_parts.append("connect-src 'self'")
        csp_parts.append("frame-src 'none'")
        csp_parts.append("object-src 'none'")
        csp_parts.append("base-uri 'self'")
        csp_parts.append("form-action 'self'")
        
        response['Content-Security-Policy'] = '; '.join(csp_parts)
        
        # Additional Tor-specific headers
        response['X-Tor-Enabled'] = 'true'
        response['X-JavaScript-Disabled'] = 'true'
        response['X-External-CDN-Disabled'] = 'true'
        
        return response


class TorRequestValidator:
    """Validates requests for Tor safety."""
    
    @staticmethod
    def validate_request(request):
        """Validate if request is safe for Tor hosting."""
        issues = []
        
        # Check for JavaScript in request
        if request.method == 'POST':
            for key, value in request.POST.items():
                if isinstance(value, str) and ('<script' in value.lower() or 'javascript:' in value.lower()):
                    issues.append(f"JavaScript detected in field: {key}")
        
        # Check for external URLs
        for key, value in request.GET.items():
            if isinstance(value, str) and value.startswith(('http://', 'https://')):
                if not value.startswith(request.build_absolute_uri('/')):
                    issues.append(f"External URL detected: {value}")
        
        return issues
    
    @staticmethod
    def sanitize_input(data):
        """Sanitize input data for Tor safety."""
        if isinstance(data, str):
            # Remove JavaScript
            data = re.sub(r'<script[^>]*>.*?</script>', '', data, flags=re.IGNORECASE | re.DOTALL)
            data = re.sub(r'javascript:', '', data, flags=re.IGNORECASE)
            data = re.sub(r'on\w+\s*=', '', data, flags=re.IGNORECASE)
            
            # Remove external URLs
            data = re.sub(r'https?://[^\s<>"]+', '[EXTERNAL_URL_BLOCKED]', data)
            
            # Remove HTML tags
            data = re.sub(r'<[^>]+>', '', data)
        
        elif isinstance(data, dict):
            return {key: TorRequestValidator.sanitize_input(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [TorRequestValidator.sanitize_input(item) for item in data]
        
        return data