"""
Custom CSRF middleware for Tor Browser compatibility
"""
from django.middleware.csrf import CsrfViewMiddleware
from django.conf import settings


class TorSafeCsrfMiddleware(CsrfViewMiddleware):
    """
    Modified CSRF middleware that handles Tor Browser's null origin
    """
    
    def _origin_verified(self, request):
        """
        Override to allow null origin for Tor Browser
        """
        import logging
        logger = logging.getLogger('csrf')
        
        request_origin = request.META.get('HTTP_ORIGIN')
        logger.info(f"CSRF check - Origin: {request_origin}, Host: {request.META.get('HTTP_HOST')}, Referer: {request.META.get('HTTP_REFERER')}")
        
        # If origin is null (Tor Browser in strict mode), check referer instead
        if request_origin == 'null' or request_origin is None:
            referer = request.META.get('HTTP_REFERER')
            if referer:
                # Extract host from referer
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                host = parsed.netloc
                
                # Check if referer host matches allowed hosts
                allowed_hosts = settings.ALLOWED_HOSTS
                if host in allowed_hosts:
                    return True
                    
                # Check against CSRF trusted origins
                for trusted_origin in settings.CSRF_TRUSTED_ORIGINS:
                    trusted_parsed = urlparse(trusted_origin)
                    if host == trusted_parsed.netloc:
                        return True
            
            # For onion addresses, also check the Host header
            host_header = request.META.get('HTTP_HOST')
            if host_header and host_header in settings.ALLOWED_HOSTS:
                return True
                
            return False
            
        # Fall back to default behavior for non-null origins
        return super()._origin_verified(request)