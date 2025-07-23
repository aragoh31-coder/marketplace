from django.urls import path
from . import views

app_name = 'wallets'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('convert/', views.convert, name='convert'),
    path('transactions/', views.transaction_history, name='transactions'),
    path('deposit/<str:currency>/', views.deposit_info, name='deposit_info'),
    path('security/', views.security_settings, name='security_settings'),
]
