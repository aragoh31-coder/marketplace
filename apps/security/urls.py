from django.urls import path
from . import views

app_name = 'security'

urlpatterns = [
    path('status/', views.security_status, name='security_status'),
    path('challenge/', views.bot_challenge, name='bot_challenge'),
    path('captcha/', views.captcha_challenge, name='captcha_challenge'),
    path('rate-limited/', views.rate_limited, name='rate_limited'),
]
