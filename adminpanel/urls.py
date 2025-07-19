from django.urls import path
from .views import (
    admin_login, admin_logout, secondary_auth, pgp_verify, locked_account,
    admin_dashboard, admin_users, admin_user_detail, admin_user_action,
    vendors_list, approve_vendor,
    products_list, delete_product,
    orders_list,
    disputes_list, resolve_dispute,
    withdrawals_list, approve_withdrawal,
    system_logs, trigger_maintenance, image_settings
)

app_name = 'adminpanel'
urlpatterns = [
    path('login/', admin_login, name='login'),
    path('logout/', admin_logout, name='logout'),
    path('secondary-auth/', secondary_auth, name='secondary_auth'),
    path('pgp-verify/', pgp_verify, name='pgp_verify'),
    path('locked/', locked_account, name='locked'),
    
    path('', admin_dashboard, name='dashboard'),
    path('dashboard/', admin_dashboard, name='dashboard'),
    path('users/', admin_users, name='users'),
    path('user/<str:username>/', admin_user_detail, name='user_detail'),
    path('user/<str:username>/action/', admin_user_action, name='user_action'),
    
    path('vendors/', vendors_list, name='vendors'),
    path('approve_vendor/<uuid:vendor_id>/', approve_vendor, name='approve_vendor'),
    path('products/', products_list, name='products'),
    path('delete_product/<uuid:product_id>/', delete_product, name='delete_product'),
    path('orders/', orders_list, name='orders'),
    path('disputes/', disputes_list, name='disputes'),
    path('resolve_dispute/<uuid:dispute_id>/', resolve_dispute, name='resolve_dispute'),
    path('withdrawals/', withdrawals_list, name='withdrawals'),
    path('approve_withdrawal/<uuid:withdrawal_id>/', approve_withdrawal, name='approve_withdrawal'),
    path('logs/', system_logs, name='logs'),
    path('maintenance/', trigger_maintenance, name='maintenance'),
    path('image-settings/', image_settings, name='image_settings'),
]
