from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('', views.vendor_list, name='list'),
    path('<int:pk>/', views.vendor_detail, name='detail'),
    path('<uuid:pk>/', views.vendor_detail, name='detail_uuid'),
    path('dashboard/', views.vendor_dashboard, name='dashboard'),
    path('apply/', views.vendor_apply, name='apply'),
]
