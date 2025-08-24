"""
Context processors for the marketplace
"""
import json
import os
from django.conf import settings
from django.core.cache import cache


def static_file_versions(request):
    """
    Add static file versions for cache busting
    """
    manifest_key = "static_manifest"
    manifest = cache.get(manifest_key)
    
    if manifest is None:
        manifest_path = os.path.join(settings.STATIC_ROOT, 'manifest.json')
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            cache.set(manifest_key, manifest, 3600)  # Cache for 1 hour
        except:
            manifest = {}
    
    def versioned_static(path):
        """Get versioned static file path"""
        if settings.DEBUG:
            return path
            
        # Use minified version in production
        if path.endswith('.css') and not path.endswith('.min.css'):
            min_path = path.replace('.css', '.min.css')
            if min_path in manifest:
                file_info = manifest.get(min_path, {})
                return f"{min_path}?v={file_info.get('hash', '1')}"
        
        file_info = manifest.get(path, {})
        return f"{path}?v={file_info.get('hash', '1')}"
    
    return {
        'versioned_static': versioned_static,
        'USE_MINIFIED': not settings.DEBUG
    }