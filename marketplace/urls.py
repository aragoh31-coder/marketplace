"""
URL configuration for marketplace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', other_app.views.Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import serve_secure_image, home, tor_safe_home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),  # Regular home
    path("core/", include("core.urls")),  # Core functionality including Tor-safe routes
    path("accounts/", include("accounts.urls")),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("products/", include("products.urls")),
    path("orders/", include("orders.urls")),
    path("wallets/", include("wallets.urls")),
    path("vendors/", include("vendors.urls")),
    path("messaging/", include("messaging.urls")),
    path("support/", include("support.urls")),
    path("adminpanel/", include("adminpanel.urls")),
    path("disputes/", include("disputes.urls")),
    path("security/", include("apps.security.urls")),
]
