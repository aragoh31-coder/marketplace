from django.urls import path
from . import views

app_name = 'captcha'

urlpatterns = [
    path('generate/', views.generate_captcha_image, name='generate'),
    path('validate/', views.validate_captcha_click, name='validate'),
    path('demo/', views.captcha_demo, name='demo'),
]