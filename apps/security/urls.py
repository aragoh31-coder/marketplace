from django.urls import path

from . import views
from . import views_dual_captcha
from . import views_advanced

app_name = "security"

urlpatterns = [
    path("status/", views.security_status, name="security_status"),
    path("dashboard/", views.user_security_dashboard, name="user_dashboard"),
    path("settings/", views.security_settings, name="settings"),
    path("bot-challenge/", views.bot_challenge, name="bot_challenge"),
    path("challenge-complete/", views.security_challenge_completion, name="challenge_completion"),
    path("challenge/", views_dual_captcha.security_challenge_dual, name="security_challenge"),
    path("test/", views.test_view, name="test_view"),
    path("test-session/", views.test_session, name="test_session"),
    path("challenge-status/", views.challenge_status, name="challenge_status"),
    path("reset-challenge/", views.reset_challenge, name="reset_challenge"),
    path("rate-limited/", views.rate_limited, name="rate_limited"),
    path("security-verification/", views.security_verification, name="security_verification"),
    path("api/status/", views.security_status_api, name="security_status_api"),
    # path("ip-change/", views.ip_change_detected, name="ip_change_detected"),  # Removed for Tor compatibility
    path("session-expired/", views.session_expired, name="session_expired"),
    
    # Advanced DDoS Protection URLs
    path('challenge/advanced/', views_advanced.advanced_challenge_verify, name='advanced_challenge_verify'),
    path('pow/verify/', views_advanced.pow_challenge_verify, name='pow_verify'),
    path('challenge/dual/', views_advanced.dual_challenge_verify, name='dual_challenge_verify'),
    path('api/token/', views_advanced.get_auth_token, name='get_auth_token'),
    path('token-usage/', views_advanced.token_usage_example, name='token_usage'),
    
    # PoW Launcher URLs
    path('pow/launcher/<str:challenge_id>/', views_advanced.pow_launcher, name='pow_launcher'),
    path('pow/download/<str:challenge_id>/', views_advanced.pow_download_solver, name='pow_download'),
    path('pow/solution/<str:challenge_id>/', views_advanced.pow_get_solution, name='pow_solution'),
    path('pow/solve/<str:challenge_id>/', views_advanced.pow_solve_endpoint, name='pow_solve'),
]
