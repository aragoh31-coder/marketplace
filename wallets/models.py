from django.db import models
from django.contrib.auth import get_user_model
from core.base_models import PrivacyModel
import uuid

User = get_user_model()


class Wallet(PrivacyModel):
    CURRENCY_CHOICES = [
        ('BTC', 'Bitcoin'),
        ('XMR', 'Monero'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    address = models.CharField(max_length=255, unique=True)
    private_key = models.TextField()  # Encrypted field
    balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    class Meta:
        unique_together = ['user', 'currency']
    
    def __str__(self):
        return f"{self.user.username} - {self.currency} Wallet"


class Transaction(PrivacyModel):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('ESCROW', 'Escrow'),
        ('RELEASE', 'Release'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    txid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    confirmations = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    def __str__(self):
        return f"{self.wallet.currency} {self.transaction_type} - {self.amount}"
