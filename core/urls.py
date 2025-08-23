"""
Core URL Configuration
Includes Tor-safe routes and core functionality.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Existing URLs
    path('', views.home, name='home'),
    path('tor/', views.tor_safe_home, name='tor_safe_home'),
    path('tor/products/', views.tor_safe_product_list, name='tor_safe_product_list'),
                # path('wallet/', views.wallet_redirect, name='wallet_redirect'),  # Removed - view doesn't exist
    
    # New advanced feature URLs
    path('loyalty/', views.loyalty_dashboard, name='loyalty_dashboard'),
    path('loyalty/rewards/', views.loyalty_rewards, name='loyalty_rewards'),
    path('analytics/', views.vendor_analytics_dashboard, name='vendor_analytics_dashboard'),
    path('recommendations/', views.product_recommendations, name='product_recommendations'),
    path('price-predictions/', views.price_predictions, name='price_predictions'),
    path('preferences/', views.user_preferences, name='user_preferences'),
    path('search/', views.advanced_search, name='advanced_search'),
    path('disputes/', views.dispute_management, name='dispute_management'),
    path('insights/', views.system_insights, name='system_insights'),
    
    # API endpoints
    path('api/preferences/update/', views.update_user_preferences, name='update_user_preferences'),
    path('api/recommendations/refresh/', views.refresh_recommendations, name='refresh_recommendations'),
]