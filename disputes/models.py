import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.base_models import PrivacyModel
from orders.models import Order

User = get_user_model()


class Dispute(PrivacyModel):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("INVESTIGATING", "Under Investigation"),
        ("AWAITING_VENDOR", "Awaiting Vendor Response"),
        ("AWAITING_BUYER", "Awaiting Buyer Response"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]
    
    RESOLUTION_CHOICES = [
        ("RELEASE_TO_VENDOR", "Release to Vendor"),
        ("REFUND_TO_BUYER", "Refund to Buyer"),
        ("PARTIAL_REFUND", "Partial Refund"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="dispute")
    complainant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="filed_disputes")
    respondent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_disputes")
    
    # Initial dispute information
    reason = models.TextField()
    
    # Buyer and vendor statements
    buyer_statement = models.TextField(blank=True)
    vendor_statement = models.TextField(blank=True)
    
    # Status and resolution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    resolution = models.TextField(blank=True)
    resolution_type = models.CharField(max_length=20, choices=RESOLUTION_CHOICES, null=True, blank=True)
    partial_refund_percentage = models.IntegerField(null=True, blank=True)
    
    # Admin handling
    moderator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderated_disputes"
    )
    admin_notes = models.TextField(blank=True)
    
    # Chat history for dispute discussion
    chat_history = models.JSONField(default=list, blank=True)
    
    # Timestamps
    resolved_at = models.DateTimeField(null=True, blank=True)

    def add_message(self, sender, message):
        """Add message to dispute chat"""
        self.chat_history.append({
            'sender': sender.username,
            'sender_id': str(sender.id),
            'message': message,
            'time': timezone.now().isoformat(),
            'is_admin': sender.is_staff
        })
        self.save(update_fields=['chat_history', 'updated_at'])
        
    def add_buyer_statement(self, statement):
        """Add or update buyer statement"""
        self.buyer_statement = statement
        self.save(update_fields=['buyer_statement', 'updated_at'])
        
    def add_vendor_statement(self, statement):
        """Add or update vendor statement"""
        self.vendor_statement = statement
        self.save(update_fields=['vendor_statement', 'updated_at'])
        
    def resolve(self, resolution_type, moderator, notes='', partial_percentage=None):
        """Resolve the dispute"""
        self.resolution_type = resolution_type
        self.moderator = moderator
        self.admin_notes = notes
        self.partial_refund_percentage = partial_percentage
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        self.save()
        
        # Update order status
        self.order.mark_disputed()
        
    def is_participant(self, user):
        """Check if user is a participant in this dispute"""
        return user == self.complainant or user == self.respondent
        
    def can_add_statement(self, user):
        """Check if user can add a statement"""
        if user == self.order.user and not self.buyer_statement:
            return True
        if user == self.order.vendor.user and not self.vendor_statement:
            return True
        return False

    def __str__(self):
        return f"Dispute {self.id} - Order {self.order.id} - {self.status}"


class DisputeEvidence(PrivacyModel):
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name="evidence")
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    steganographic_data = models.TextField(blank=True, null=True)  # Encrypted field
    file_attachment = models.FileField(upload_to="dispute_evidence/", blank=True, null=True)
    
    # Add evidence type
    EVIDENCE_TYPE_CHOICES = [
        ("SCREENSHOT", "Screenshot"),
        ("BLOCKCHAIN_TX", "Blockchain Transaction"),
        ("COMMUNICATION", "Communication Log"),
        ("OTHER", "Other"),
    ]
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPE_CHOICES, default="OTHER")

    def __str__(self):
        return f"Evidence for Dispute {self.dispute.id} by {self.submitted_by.username}"
