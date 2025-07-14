from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required


def require_vendor(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'vendor'):
            return HttpResponseForbidden("Vendor access required")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def require_signed_url(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view
