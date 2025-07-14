from django.db import models
from django.contrib.auth import get_user_model
from core.base_models import PrivacyModel
import uuid

User = get_user_model()


class Vendor(PrivacyModel):
    TRUST_LEVELS = [
        ('NEW', 'New Vendor'),
        ('TRUSTED', 'Trusted'),
        ('VERIFIED', 'Verified'),
        ('PREMIUM', 'Premium'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor')
    vendor_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    trust_level = models.CharField(max_length=20, choices=TRUST_LEVELS, default='NEW')
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return self.vendor_name


class VendorRating(PrivacyModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['vendor', 'user']
    
    def __str__(self):
        return f"{self.vendor.vendor_name} - {self.rating}/5"
