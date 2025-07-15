from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/pgp/', views.pgp_settings, name='pgp_settings'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('profile/login-history/', views.login_history_view, name='login_history'),
    path('pgp-challenge/', views.pgp_challenge_view, name='pgp_challenge'),
]
