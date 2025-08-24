import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.base_models import PrivacyModel
from products.models import Product
from vendors.models import Vendor

User = get_user_model()


class Order(PrivacyModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending Payment"),
        ("PAID", "Paid"),
        ("PROCESSING", "Processing"),
        ("LOCKED", "Funds Locked in Escrow"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("DISPUTED", "Disputed"),
        ("REFUNDED", "Refunded"),
    ]

    CURRENCY_CHOICES = [
        ("BTC", "Bitcoin"),
        ("XMR", "Monero"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="vendor_orders", null=True)
    buyer_wallet = models.ForeignKey(
        "wallets.Wallet", on_delete=models.CASCADE, related_name="buyer_orders", null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    total_btc = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_xmr = models.DecimalField(max_digits=20, decimal_places=12, default=0)
    currency_used = models.CharField(max_length=3, choices=CURRENCY_CHOICES, null=True, blank=True)
    escrow_address = models.CharField(max_length=255, blank=True, null=True)
    shipping_address = models.TextField(blank=True)  # Encrypted field

    # Escrow and timing fields
    locked_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    escrow_released = models.BooleanField(default=False)
    auto_finalize_at = models.DateTimeField(null=True, blank=True)

    # Add vendor field explicitly if not already linked through items
    quantity = models.IntegerField(default=1)

    def lock_funds(self):
        """Lock funds in escrow when buyer pays"""
        self.status = 'LOCKED'
        self.locked_at = timezone.now()
        # Auto-finalize after 14 days if not disputed
        self.auto_finalize_at = timezone.now() + timezone.timedelta(days=14)
        self.save(update_fields=['status', 'locked_at', 'auto_finalize_at'])

    def mark_shipped(self):
        """Mark order as shipped by vendor"""
        self.status = 'SHIPPED'
        self.shipped_at = timezone.now()
        # Reset auto-finalize timer to 14 days from shipment
        self.auto_finalize_at = timezone.now() + timezone.timedelta(days=14)
        self.save(update_fields=['status', 'shipped_at', 'auto_finalize_at'])

    def mark_completed(self):
        """Mark order as completed and release escrow"""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.escrow_released = True
        self.save(update_fields=['status', 'completed_at', 'escrow_released'])

    def mark_disputed(self):
        """Mark order as disputed"""
        self.status = 'DISPUTED'
        self.auto_finalize_at = None  # Stop auto-finalization
        self.save(update_fields=['status', 'auto_finalize_at'])

    def mark_refunded(self):
        """Mark order as refunded"""
        self.status = 'REFUNDED'
        self.refunded_at = timezone.now()
        self.escrow_released = True
        self.save(update_fields=['status', 'refunded_at', 'escrow_released'])

    def can_dispute(self):
        """Check if order can be disputed"""
        return self.status in ['LOCKED', 'PROCESSING', 'SHIPPED']

    def can_finalize(self):
        """Check if order can be finalized"""
        return self.status == 'SHIPPED' and not self.escrow_released

    def __str__(self):
        return f"Order {self.id} - {self.user.username} - {self.status}"


class OrderItem(PrivacyModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price_btc = models.DecimalField(max_digits=20, decimal_places=8)
    price_xmr = models.DecimalField(max_digits=20, decimal_places=12)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


class Cart(PrivacyModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")

    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(PrivacyModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ["cart", "product"]

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in cart"
