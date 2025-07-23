from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
import re
import time

class SecurityMiddleware(MiddlewareMixin):
    """Additional security middleware"""
    
    BOT_USER_AGENTS = [
        r'.*bot.*', r'.*crawler.*', r'.*spider.*', r'.*scraper.*',
        r'curl', r'wget', r'python-requests', r'http', r'test'
    ]
    
    SUSPICIOUS_PATTERNS = [
        r'/admin', r'/wp-admin', r'\.php$', r'\.asp$',
        r'/config', r'/backup', r'\.sql$'
    ]

    def process_request(self, request):
        """Process incoming requests for security threats"""
        
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
        
        return None

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
