from django.db import models
from django.contrib.auth import get_user_model
from core.base_models import PrivacyModel
import uuid

User = get_user_model()


class AdminLog(PrivacyModel):
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    target_model = models.CharField(max_length=100)
    target_id = models.CharField(max_length=255)
    description = models.TextField()
    ip_address = models.GenericIPAddressField()
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.action_type} {self.target_model}"


class SystemSettings(PrivacyModel):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"
