from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_view, name="cart"),
    path("add-to-cart/<uuid:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("create/", views.create_order, name="create"),
    path("", views.order_list, name="list"),
    path("<uuid:pk>/", views.order_detail, name="detail"),
    path("<uuid:pk>/confirm/", views.confirm_receipt, name="confirm"),
    path("<uuid:pk>/ship/", views.mark_shipped, name="mark_shipped"),
    path("<uuid:pk>/dispute/", views.raise_dispute, name="raise_dispute"),
]
