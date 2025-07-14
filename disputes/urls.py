from django.urls import path
from . import views

app_name = 'disputes'

urlpatterns = [
    path('', views.dispute_list, name='list'),
    path('create/<int:order_id>/', views.create_dispute, name='create'),
    path('<int:dispute_id>/', views.dispute_detail, name='detail'),
]
