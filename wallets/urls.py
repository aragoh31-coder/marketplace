from django.urls import path
from . import views

app_name = 'wallets'

urlpatterns = [
    path('', views.deposit, name='list'),
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('transactions/', views.transaction_list, name='transactions'),
]
