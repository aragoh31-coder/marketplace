from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.message_list, name='list'),
    path('compose/', views.compose_message, name='compose'),
    path('<uuid:pk>/', views.message_detail, name='detail'),
]
