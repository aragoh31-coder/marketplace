from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('', views.vendor_list, name='list'),
    path('<uuid:pk>/', views.vendor_detail, name='detail'),
    path('dashboard/', views.vendor_dashboard, name='dashboard'),
    path('notifications/', views.vendor_notifications, name='notifications'),
    path('feedback/', views.vendor_feedback, name='feedback'),
    path('feedback/<uuid:feedback_id>/respond/', views.respond_feedback, name='respond_feedback'),
    path('apply/', views.vendor_apply, name='apply'),
]
