"""
Context Processors for Tor Safety
Provides Tor-specific context variables to all templates.
"""

from django.conf import settings


def tor_safe_context(request):
    """
    Context processor to provide Tor-safe variables.
    Available in all templates automatically.
    """
    return {
        'tor_enabled': getattr(settings, 'TOR_SAFE_CONTEXT', {}).get('tor_enabled', True),
        'javascript_disabled': getattr(settings, 'TOR_SAFE_CONTEXT', {}).get('javascript_disabled', True),
        'external_cdns_disabled': getattr(settings, 'TOR_SAFE_CONTEXT', {}).get('external_cdns_disabled', True),
        'analytics_disabled': getattr(settings, 'TOR_SAFE_CONTEXT', {}).get('analytics_disabled', True),
        'tor_browser_detected': _detect_tor_browser(request),
        'security_level': _get_security_level(request),
    }


def _detect_tor_browser(request):
    """Detect if user is using Tor Browser."""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # Tor Browser indicators
    tor_indicators = [
        'tor',
        'firefox/102',  # Tor Browser version
        'firefox/115',  # Tor Browser version
        'firefox/120',  # Tor Browser version
    ]
    
    return any(indicator in user_agent for indicator in tor_indicators)


def _get_security_level(request):
    """Determine security level based on request."""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    if 'tor' in user_agent:
        return 'tor_safest'
    elif 'firefox' in user_agent:
        return 'firefox_standard'
    else:
        return 'other_browser'