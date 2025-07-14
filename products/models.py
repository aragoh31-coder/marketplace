from django.db import models
from django.contrib.auth import get_user_model
from core.base_models import PrivacyModel
from vendors.models import Vendor
import uuid

User = get_user_model()


class Category(PrivacyModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"


class Product(PrivacyModel):
    PRODUCT_TYPES = [
        ('GIFT_CARD', 'Gift Card'),
        ('DIGITAL', 'Digital Product'),
        ('PHYSICAL', 'Physical Product'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='GIFT_CARD')
    price_btc = models.DecimalField(max_digits=20, decimal_places=8)
    price_xmr = models.DecimalField(max_digits=20, decimal_places=8)
    stock_quantity = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    steganography_data = models.TextField(blank=True, null=True)  # Encrypted field
    
    def __str__(self):
        return f"{self.name} - {self.vendor.vendor_name}"


class ProductImage(PrivacyModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Image for {self.product.name}"
