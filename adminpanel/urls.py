from django.urls import path
from .views import (
    dashboard, users_list, user_detail, ban_user,
    vendors_list, approve_vendor,
    products_list, delete_product,
    orders_list,
    disputes_list, resolve_dispute,
    withdrawals_list, approve_withdrawal,
    system_logs, trigger_maintenance
)

app_name = 'adminpanel'
urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('dashboard/', dashboard, name='dashboard'),
    path('users/', users_list, name='users'),
    path('user/<uuid:user_id>/', user_detail, name='user_detail'),
    path('ban_user/<uuid:user_id>/', ban_user, name='ban_user'),
    path('vendors/', vendors_list, name='vendors'),
    path('approve_vendor/<int:vendor_id>/', approve_vendor, name='approve_vendor'),
    path('products/', products_list, name='products'),
    path('delete_product/<int:product_id>/', delete_product, name='delete_product'),
    path('orders/', orders_list, name='orders'),
    path('disputes/', disputes_list, name='disputes'),
    path('resolve_dispute/<int:dispute_id>/', resolve_dispute, name='resolve_dispute'),
    path('withdrawals/', withdrawals_list, name='withdrawals'),
    path('approve_withdrawal/<int:withdrawal_id>/', approve_withdrawal, name='approve_withdrawal'),
    path('logs/', system_logs, name='logs'),
    path('maintenance/', trigger_maintenance, name='maintenance'),
]
