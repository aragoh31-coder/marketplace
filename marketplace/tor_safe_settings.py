"""
Tor-Safe Django Settings
Optimized for hosting behind Tor with maximum security and privacy.
"""

import os
from pathlib import Path
from .settings import *

# Override base settings for Tor safety
DEBUG = False
ALLOWED_HOSTS = ['*']  # Allow all hosts for Tor

# Security Headers for Tor
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'no-referrer'
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security Policy - Strict for Tor
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'none'",)  # No JavaScript allowed
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_SRC = ("'none'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)

# Disable all external services
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CELERY_BROKER_URL = None
CELERY_RESULT_BACKEND = None

# Disable analytics and tracking
GOOGLE_ANALYTICS = None
GOOGLE_TAG_MANAGER = None
FACEBOOK_PIXEL = None

# Disable social authentication
SOCIAL_AUTH_DISABLED = True

# Disable external CDNs
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Tor-specific middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom Tor security middleware
    'core.security.middleware.TorSecurityMiddleware',
]

# Disable JavaScript in templates
TEMPLATES[0]['OPTIONS']['context_processors'].append(
    'core.context_processors.tor_safe_context'
)

# Static files - local only
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files - local only
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Database - SQLite for Tor (no external connections)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Cache - local memory only
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Session settings for Tor
SESSION_COOKIE_SECURE = False  # Tor handles HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF settings for Tor
CSRF_COOKIE_SECURE = False  # Tor handles HTTPS
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = ['http://localhost', 'http://127.0.0.1']

# Logging - local files only
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'tor_marketplace.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}

# Disable external APIs
BITCOIND_RPC_URL = None
REDIS_URL = None

# Tor-specific apps
TOR_SAFE_APPS = [
    'core',
    'accounts',
    'wallets',
    'vendors',
    'products',
    'orders',
    'disputes',
    'messaging',
    'support',
    'adminpanel',
]

# Override installed apps for Tor safety
INSTALLED_APPS = [app for app in INSTALLED_APPS if app in TOR_SAFE_APPS]

# Disable Django Debug Toolbar
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS.remove('debug_toolbar')

# Disable Django Extensions
if 'django_extensions' in INSTALLED_APPS:
    INSTALLED_APPS.remove('django_extensions')

# Tor-specific context
TOR_SAFE_CONTEXT = {
    'tor_enabled': True,
    'javascript_disabled': True,
    'external_cdns_disabled': True,
    'analytics_disabled': True,
}