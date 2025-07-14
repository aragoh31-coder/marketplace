from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    path('', views.support_home, name='home'),
    path('tickets/', views.ticket_list, name='tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('feedback/', views.submit_feedback, name='feedback'),
]
