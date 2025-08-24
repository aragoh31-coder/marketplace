"""
Advanced Anti-DDoS Middleware with Stateless Protection
"""
import json
import logging
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from .antiddos_advanced import AdvancedDDoSProtection, BlindTokenBucket

logger = logging.getLogger('marketplace.security.ddos.middleware')


class AdvancedDDoSMiddleware(MiddlewareMixin):
    """Middleware implementing advanced DDoS protection"""
    
    # Paths that bypass DDoS protection
    BYPASS_PATHS = [
        '/static/',
        '/media/',
        '/security/challenge/',
        '/security/pow/',
        '/security/verify/',
        '/admin/challenge/',
    ]
    
    def process_request(self, request):
        """Process incoming request with advanced DDoS protection"""
        
        # Skip protection for bypass paths
        for path in self.BYPASS_PATHS:
            if request.path.startswith(path):
                return None
        
        # Check request with advanced protection
        is_allowed, block_reason, metadata = AdvancedDDoSProtection.check_request(request)
        
        if is_allowed:
            # Store token in request for response headers
            if metadata.get('method') == 'token':
                request.ddos_token_used = True
            return None
        
        # Handle different block reasons
        if block_reason == 'low_reputation':
            # Require Proof of Work
            return self._handle_pow_challenge(request, metadata)
        
        elif block_reason == 'rate_limit_circuit':
            # Require standard challenge
            return self._handle_challenge(request, metadata)
        
        elif block_reason == 'suspicious_pattern':
            # Require dual challenge
            return self._handle_dual_challenge(request, metadata)
        
        else:
            # Generic block
            return self._handle_blocked(request, block_reason, metadata)
    
    def process_response(self, request, response):
        """Add security headers to response"""
        
        # Add rate limit headers
        if hasattr(request, 'ddos_token_used'):
            response['X-RateLimit-Method'] = 'token'
        
        # Add security challenge headers if needed
        if hasattr(request, 'ddos_challenge_issued'):
            response['X-Challenge-Required'] = request.ddos_challenge_issued
        
        return response
    
    def _handle_pow_challenge(self, request, metadata):
        """Handle Proof of Work challenge requirement"""
        
        # Store current path for redirect after challenge
        request.session['ddos_redirect_after'] = request.get_full_path()
        
        # Generate PoW challenge
        challenge_data = AdvancedDDoSProtection.issue_challenge(request, 'pow')
        
        # Mark challenge issued
        request.ddos_challenge_issued = 'pow'
        
        # Render PoW challenge page
        return render(request, 'security/pow_challenge.html', {
            'challenge': challenge_data,
            'metadata': metadata,
            'difficulty': challenge_data['challenge'].get('pow_data', {}).get('difficulty', 4)
        })
    
    def _handle_challenge(self, request, metadata):
        """Handle standard challenge requirement"""
        
        # Store current path
        request.session['ddos_redirect_after'] = request.get_full_path()
        
        # Generate math challenge
        challenge_data = AdvancedDDoSProtection.issue_challenge(request, 'math')
        
        # Mark challenge issued
        request.ddos_challenge_issued = 'math'
        
        # For AJAX requests, return JSON
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'challenge_required',
                'challenge': challenge_data,
                'metadata': metadata
            }, status=429)
        
        # Render challenge page
        return render(request, 'security/advanced_challenge.html', {
            'challenge': challenge_data,
            'metadata': metadata
        })
    
    def _handle_dual_challenge(self, request, metadata):
        """Handle dual challenge requirement"""
        
        # Store current path
        request.session['ddos_redirect_after'] = request.get_full_path()
        
        # Generate both challenges
        math_challenge = AdvancedDDoSProtection.issue_challenge(request, 'math')
        
        # Mark challenge issued
        request.ddos_challenge_issued = 'dual'
        
        # Render dual challenge page
        return render(request, 'security/challenge_required_dual_advanced.html', {
            'math_challenge': math_challenge,
            'metadata': metadata,
            'reason': metadata.get('reason', 'suspicious_pattern')
        })
    
    def _handle_blocked(self, request, reason, metadata):
        """Handle blocked request"""
        
        logger.warning(f"Request blocked: {reason} - {metadata}")
        
        # For AJAX requests
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'blocked',
                'reason': reason,
                'metadata': metadata
            }, status=403)
        
        # Render block page
        return render(request, 'security/blocked_advanced.html', {
            'reason': reason,
            'metadata': metadata
        }, status=403)