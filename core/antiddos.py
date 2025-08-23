"""
Comprehensive Anti-DDoS Protection System
"""
import time
import hashlib
import logging
from collections import defaultdict
from typing import Dict, Tuple, Optional
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from core.security_utils import RateLimiter, TokenGenerator

logger = logging.getLogger('marketplace.security.ddos')


class DDoSProtection:
    """
    Multi-layered DDoS protection system with:
    - Progressive rate limiting
    - Suspicious pattern detection
    - Distributed attack mitigation
    - Automatic blacklisting
    - Challenge-response system
    """
    
    # Rate limit configurations
    RATE_LIMITS = {
        'global': {
            'requests_per_second': 10,
            'requests_per_minute': 100,
            'requests_per_hour': 1000,
        },
        'per_ip': {
            'requests_per_second': 5,
            'requests_per_minute': 50,
            'requests_per_hour': 500,
        },
        'per_user': {
            'requests_per_second': 3,
            'requests_per_minute': 30,
            'requests_per_hour': 300,
        },
        'sensitive_endpoints': {
            '/login': {'requests_per_minute': 5, 'requests_per_hour': 20},
            '/register': {'requests_per_minute': 3, 'requests_per_hour': 10},
            '/wallets/withdraw': {'requests_per_minute': 2, 'requests_per_hour': 10},
            '/api': {'requests_per_minute': 20, 'requests_per_hour': 200},
        }
    }
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = {
        'rapid_endpoint_switching': 10,  # Max different endpoints per minute
        'failed_auth_attempts': 5,  # Max failed auths before temp ban
        'error_rate': 0.5,  # Max error rate (50%)
        'identical_requests': 20,  # Max identical requests per minute
    }
    
    @classmethod
    def check_request(cls, request) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Check if request should be allowed
        Returns: (is_allowed, block_reason, metadata)
        """
        ip = cls._get_client_ip(request)
        user_id = str(request.user.id) if request.user.is_authenticated else None
        
        # Check if IP is blacklisted
        if cls._is_blacklisted(ip):
            logger.warning(f"Blacklisted IP attempted access: {ip}")
            return False, "blacklisted", {"ip": ip}
        
        # Check global rate limits
        is_allowed, reason = cls._check_global_limits()
        if not is_allowed:
            return False, reason, {"ip": ip}
        
        # Check per-IP rate limits
        is_allowed, reason = cls._check_ip_limits(ip)
        if not is_allowed:
            cls._increment_violation_score(ip, 1)
            return False, reason, {"ip": ip}
        
        # Check per-user rate limits (if authenticated)
        if user_id:
            is_allowed, reason = cls._check_user_limits(user_id)
            if not is_allowed:
                return False, reason, {"ip": ip, "user_id": user_id}
        
        # Check endpoint-specific limits
        is_allowed, reason = cls._check_endpoint_limits(request.path, ip)
        if not is_allowed:
            cls._increment_violation_score(ip, 2)
            return False, reason, {"ip": ip, "endpoint": request.path}
        
        # Check for suspicious patterns
        is_suspicious, pattern = cls._detect_suspicious_patterns(request, ip)
        if is_suspicious:
            cls._increment_violation_score(ip, 3)
            return False, f"suspicious_pattern:{pattern}", {"ip": ip, "pattern": pattern}
        
        # Check violation score for auto-blacklisting
        if cls._should_blacklist(ip):
            cls._blacklist_ip(ip, duration=3600)  # 1 hour
            return False, "auto_blacklisted", {"ip": ip}
        
        # All checks passed
        cls._track_request(request, ip)
        return True, None, {"ip": ip}
    
    @classmethod
    def _check_global_limits(cls) -> Tuple[bool, Optional[str]]:
        """Check global rate limits across all requests"""
        current_time = time.time()
        
        # Check requests per second
        second_key = f"ddos:global:second:{int(current_time)}"
        second_count = cache.get(second_key, 0)
        if second_count >= cls.RATE_LIMITS['global']['requests_per_second']:
            return False, "global_rate_limit_second"
        cache.set(second_key, second_count + 1, 2)
        
        # Check requests per minute
        minute_key = f"ddos:global:minute:{int(current_time / 60)}"
        minute_count = cache.get(minute_key, 0)
        if minute_count >= cls.RATE_LIMITS['global']['requests_per_minute']:
            return False, "global_rate_limit_minute"
        cache.set(minute_key, minute_count + 1, 65)
        
        return True, None
    
    @classmethod
    def _check_ip_limits(cls, ip: str) -> Tuple[bool, Optional[str]]:
        """Check per-IP rate limits"""
        current_time = time.time()
        
        # Check requests per second
        second_key = f"ddos:ip:{ip}:second:{int(current_time)}"
        second_count = cache.get(second_key, 0)
        if second_count >= cls.RATE_LIMITS['per_ip']['requests_per_second']:
            logger.warning(f"IP {ip} exceeded per-second limit")
            return False, "ip_rate_limit_second"
        cache.set(second_key, second_count + 1, 2)
        
        # Check requests per minute
        minute_key = f"ddos:ip:{ip}:minute:{int(current_time / 60)}"
        minute_count = cache.get(minute_key, 0)
        if minute_count >= cls.RATE_LIMITS['per_ip']['requests_per_minute']:
            logger.warning(f"IP {ip} exceeded per-minute limit")
            return False, "ip_rate_limit_minute"
        cache.set(minute_key, minute_count + 1, 65)
        
        # Check requests per hour
        hour_key = f"ddos:ip:{ip}:hour:{int(current_time / 3600)}"
        hour_count = cache.get(hour_key, 0)
        if hour_count >= cls.RATE_LIMITS['per_ip']['requests_per_hour']:
            logger.warning(f"IP {ip} exceeded per-hour limit")
            return False, "ip_rate_limit_hour"
        cache.set(hour_key, hour_count + 1, 3650)
        
        return True, None
    
    @classmethod
    def _check_user_limits(cls, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check per-user rate limits"""
        current_time = time.time()
        
        # Similar to IP limits but for authenticated users
        minute_key = f"ddos:user:{user_id}:minute:{int(current_time / 60)}"
        minute_count = cache.get(minute_key, 0)
        if minute_count >= cls.RATE_LIMITS['per_user']['requests_per_minute']:
            logger.warning(f"User {user_id} exceeded per-minute limit")
            return False, "user_rate_limit_minute"
        cache.set(minute_key, minute_count + 1, 65)
        
        return True, None
    
    @classmethod
    def _check_endpoint_limits(cls, path: str, ip: str) -> Tuple[bool, Optional[str]]:
        """Check endpoint-specific rate limits"""
        # Check if this endpoint has specific limits
        for endpoint, limits in cls.RATE_LIMITS['sensitive_endpoints'].items():
            if path.startswith(endpoint):
                current_time = time.time()
                
                # Check per-minute limit
                if 'requests_per_minute' in limits:
                    minute_key = f"ddos:endpoint:{endpoint}:{ip}:minute:{int(current_time / 60)}"
                    minute_count = cache.get(minute_key, 0)
                    if minute_count >= limits['requests_per_minute']:
                        logger.warning(f"IP {ip} exceeded endpoint {endpoint} per-minute limit")
                        return False, f"endpoint_rate_limit:{endpoint}"
                    cache.set(minute_key, minute_count + 1, 65)
                
                # Check per-hour limit
                if 'requests_per_hour' in limits:
                    hour_key = f"ddos:endpoint:{endpoint}:{ip}:hour:{int(current_time / 3600)}"
                    hour_count = cache.get(hour_key, 0)
                    if hour_count >= limits['requests_per_hour']:
                        logger.warning(f"IP {ip} exceeded endpoint {endpoint} per-hour limit")
                        return False, f"endpoint_rate_limit:{endpoint}"
                    cache.set(hour_key, hour_count + 1, 3650)
        
        return True, None
    
    @classmethod
    def _detect_suspicious_patterns(cls, request, ip: str) -> Tuple[bool, Optional[str]]:
        """Detect suspicious request patterns"""
        current_time = time.time()
        minute_window = int(current_time / 60)
        
        # Track endpoint access pattern
        endpoint_key = f"ddos:pattern:endpoints:{ip}:{minute_window}"
        endpoints = cache.get(endpoint_key, set())
        endpoints.add(request.path)
        cache.set(endpoint_key, endpoints, 65)
        
        if len(endpoints) > cls.SUSPICIOUS_PATTERNS['rapid_endpoint_switching']:
            logger.warning(f"IP {ip} accessing too many endpoints: {len(endpoints)}")
            return True, "rapid_endpoint_switching"
        
        # Track identical requests
        request_hash = cls._hash_request(request)
        identical_key = f"ddos:pattern:identical:{ip}:{request_hash}:{minute_window}"
        identical_count = cache.get(identical_key, 0)
        cache.set(identical_key, identical_count + 1, 65)
        
        if identical_count > cls.SUSPICIOUS_PATTERNS['identical_requests']:
            logger.warning(f"IP {ip} sending too many identical requests")
            return True, "identical_requests"
        
        # Track error rate
        error_key = f"ddos:pattern:errors:{ip}:{minute_window}"
        error_data = cache.get(error_key, {'total': 0, 'errors': 0})
        
        # This will be updated by the response middleware
        if error_data['total'] > 10:  # Minimum requests before checking error rate
            error_rate = error_data['errors'] / error_data['total']
            if error_rate > cls.SUSPICIOUS_PATTERNS['error_rate']:
                logger.warning(f"IP {ip} has high error rate: {error_rate:.2%}")
                return True, "high_error_rate"
        
        return False, None
    
    @classmethod
    def _track_request(cls, request, ip: str):
        """Track request for pattern analysis"""
        current_time = time.time()
        minute_window = int(current_time / 60)
        
        # Track total requests for error rate calculation
        error_key = f"ddos:pattern:errors:{ip}:{minute_window}"
        error_data = cache.get(error_key, {'total': 0, 'errors': 0})
        error_data['total'] += 1
        cache.set(error_key, error_data, 65)
        
        # Store request metadata for analysis
        request_data = {
            'path': request.path,
            'method': request.method,
            'timestamp': current_time,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        
        history_key = f"ddos:history:{ip}"
        history = cache.get(history_key, [])
        history.append(request_data)
        # Keep last 100 requests
        history = history[-100:]
        cache.set(history_key, history, 3600)
    
    @classmethod
    def track_response_error(cls, request, ip: str, status_code: int):
        """Track error responses for pattern detection"""
        if status_code >= 400:
            current_time = time.time()
            minute_window = int(current_time / 60)
            
            error_key = f"ddos:pattern:errors:{ip}:{minute_window}"
            error_data = cache.get(error_key, {'total': 0, 'errors': 0})
            error_data['errors'] += 1
            cache.set(error_key, error_data, 65)
    
    @classmethod
    def _increment_violation_score(cls, ip: str, score: int):
        """Increment violation score for an IP"""
        score_key = f"ddos:violation_score:{ip}"
        current_score = cache.get(score_key, 0)
        new_score = current_score + score
        cache.set(score_key, new_score, 3600)  # Reset after 1 hour
        
        logger.info(f"IP {ip} violation score: {new_score}")
    
    @classmethod
    def _should_blacklist(cls, ip: str) -> bool:
        """Check if IP should be auto-blacklisted based on violation score"""
        score_key = f"ddos:violation_score:{ip}"
        score = cache.get(score_key, 0)
        return score >= 10  # Threshold for auto-blacklisting
    
    @classmethod
    def _blacklist_ip(cls, ip: str, duration: int = 3600):
        """Add IP to blacklist"""
        blacklist_key = f"ddos:blacklist:{ip}"
        cache.set(blacklist_key, True, duration)
        logger.warning(f"IP {ip} has been blacklisted for {duration} seconds")
        
        # Log to persistent storage if needed
        cls._log_blacklist_event(ip, duration)
    
    @classmethod
    def _is_blacklisted(cls, ip: str) -> bool:
        """Check if IP is blacklisted"""
        blacklist_key = f"ddos:blacklist:{ip}"
        return cache.get(blacklist_key, False)
    
    @classmethod
    def _get_client_ip(cls, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    @classmethod
    def _hash_request(cls, request) -> str:
        """Create hash of request for duplicate detection"""
        data = f"{request.method}:{request.path}:{request.GET.urlencode()}:{request.body[:100]}"
        return hashlib.md5(data.encode()).hexdigest()
    
    @classmethod
    def _log_blacklist_event(cls, ip: str, duration: int):
        """Log blacklist event for analysis"""
        event = {
            'ip': ip,
            'timestamp': timezone.now(),
            'duration': duration,
            'reason': 'auto_blacklist',
        }
        # In production, save to database or external logging service
        logger.error(f"BLACKLIST EVENT: {event}")
    
    @classmethod
    def get_protection_stats(cls) -> Dict:
        """Get current protection statistics"""
        stats = {
            'blacklisted_ips': 0,
            'current_requests_per_minute': 0,
            'blocked_requests_last_hour': 0,
            'top_violators': [],
        }
        
        # Count blacklisted IPs
        # This is a simplified version - in production, use a more efficient method
        blacklist_pattern = "ddos:blacklist:*"
        # Note: cache.keys() is not available in all cache backends
        # In production, maintain a separate counter
        
        # Get current global request rate
        current_time = time.time()
        minute_key = f"ddos:global:minute:{int(current_time / 60)}"
        stats['current_requests_per_minute'] = cache.get(minute_key, 0)
        
        return stats


class DDoSProtectionMiddleware:
    """Middleware to integrate DDoS protection with Django"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.whitelist_paths = [
            '/static/',
            '/media/',
            '/security/challenge/',
            '/security/blocked/',
        ]
    
    def __call__(self, request):
        # Skip protection for whitelisted paths
        for path in self.whitelist_paths:
            if request.path.startswith(path):
                return self.get_response(request)
        
        # Check DDoS protection
        is_allowed, block_reason, metadata = DDoSProtection.check_request(request)
        
        if not is_allowed:
            logger.warning(f"Request blocked - Reason: {block_reason}, Metadata: {metadata}")
            
            # Different responses based on block reason
            if block_reason == "blacklisted":
                return HttpResponse("Your IP has been blacklisted.", status=403)
            elif "rate_limit" in block_reason:
                return render(request, 'security/rate_limited_enhanced.html', {
                    'reason': block_reason,
                    'retry_after': 60,
                })
            elif "suspicious_pattern" in block_reason:
                # Redirect to challenge page
                return render(request, 'security/challenge_required.html', {
                    'reason': block_reason,
                })
            else:
                return HttpResponse("Access denied.", status=403)
        
        # Process request
        response = self.get_response(request)
        
        # Track response for pattern analysis
        ip = DDoSProtection._get_client_ip(request)
        DDoSProtection.track_response_error(request, ip, response.status_code)
        
        return response