"""
Core URL Configuration
Includes Tor-safe routes and core functionality.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Tor-safe routes
    path('tor/', views.tor_safe_home, name='tor_home'),
    path('tor/products/', views.tor_safe_product_list, name='tor_products'),
    path('tor/login/', views.tor_safe_login, name='tor_login'),
    path('tor/wallet/', views.tor_safe_wallet_detail, name='tor_wallet'),
    
    # Core functionality
    path('secure-images/<path:path>', views.serve_secure_image, name='secure_image'),
]