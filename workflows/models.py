# workflows/models.py
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from accounts.models import User, TimestampedModel

# ============================================
# APPROVAL WORKFLOW
# ============================================
class ApprovalWorkflow(TimestampedModel):
    """Generic approval workflow for any entity"""
    
    WORKFLOW_TYPE_CHOICES = [
        ('investment', 'Investment Approval'),
        ('property', 'Property Approval'),
        ('redemption', 'Redemption Approval'),
        ('payout', 'Payout Approval'),
        ('kyc', 'KYC Approval'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    

    
    workflow_type = models.CharField(max_length=20, choices=WORKFLOW_TYPE_CHOICES)
    
    # Generic relation to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Requester
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_workflows')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Reviewer
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_workflows')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_workflows')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    request_notes = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'approval_workflows'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.workflow_type} - {self.status}"
