from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from core.base_models import PrivacyModel
import uuid


class User(AbstractUser, PrivacyModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pgp_public_key = models.TextField(blank=True, null=True)
    panic_password = models.CharField(max_length=128, blank=True, null=True)
    session_fingerprint = models.CharField(max_length=255, blank=True, null=True)
    last_activity = models.DateTimeField(default=timezone.now)
    failed_login_attempts = models.IntegerField(default=0)
    is_vendor = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username


class UserSession(PrivacyModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    fingerprint = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    last_activity = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.session_key[:8]}"
