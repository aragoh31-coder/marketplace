from django.urls import path

from . import views

app_name = "security"

urlpatterns = [
    path("status/", views.security_status, name="security_status"),
    path("dashboard/", views.user_security_dashboard, name="user_dashboard"),
    path("settings/", views.security_settings, name="settings"),
    path("bot-challenge/", views.bot_challenge, name="bot_challenge"),
    path("challenge-complete/", views.security_challenge_completion, name="challenge_completion"),
    path("challenge/", views.security_challenge, name="security_challenge"),
    path("test/", views.test_view, name="test_view"),
    path("test-session/", views.test_session, name="test_session"),
    path("challenge-status/", views.challenge_status, name="challenge_status"),
    path("reset-challenge/", views.reset_challenge, name="reset_challenge"),
    path("rate-limited/", views.rate_limited, name="rate_limited"),
    path("security-verification/", views.security_verification, name="security_verification"),
    path("api/status/", views.security_status_api, name="security_status_api"),
    path("ip-change/", views.ip_change_detected, name="ip_change_detected"),
    path("session-expired/", views.session_expired, name="session_expired"),
]
