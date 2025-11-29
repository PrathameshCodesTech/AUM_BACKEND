"""
Compliance Models
KYC, Documents, and Audit Log models
"""
from django.db import models  # ← THIS LINE IS CRITICAL!
from accounts.models import User, TimestampedModel, SoftDeleteModel


class KYC(TimestampedModel, SoftDeleteModel):
    """Know Your Customer (KYC) details for users"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='kyc'
    )
    
    # Aadhaar Details
    aadhaar_number = models.CharField(max_length=12, blank=True, null=True)
    aadhaar_name = models.CharField(max_length=200, blank=True, null=True)
    aadhaar_dob = models.DateField(blank=True, null=True)
    aadhaar_gender = models.CharField(max_length=10, blank=True, null=True)
    aadhaar_address = models.TextField(blank=True, null=True)
    aadhaar_verified = models.BooleanField(default=False)
    aadhaar_verified_at = models.DateTimeField(blank=True, null=True)
    aadhaar_front = models.FileField(upload_to='kyc/aadhaar/', blank=True, null=True)
    aadhaar_back = models.FileField(upload_to='kyc/aadhaar/', blank=True, null=True)
    
    # PAN Details
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    pan_name = models.CharField(max_length=200, blank=True, null=True)
    pan_father_name = models.CharField(max_length=200, blank=True, null=True)
    pan_dob = models.DateField(blank=True, null=True)
    pan_verified = models.BooleanField(default=False)
    pan_verified_at = models.DateTimeField(blank=True, null=True)
    pan_aadhaar_linked = models.BooleanField(default=False)
    pan_document = models.FileField(upload_to='kyc/pan/', blank=True, null=True)
    
    # Bank Details
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=20, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11, blank=True, null=True)
    account_holder_name = models.CharField(max_length=200, blank=True, null=True)
    account_type = models.CharField(max_length=20, blank=True, null=True)
    bank_verified = models.BooleanField(default=False)
    bank_verified_at = models.DateTimeField(blank=True, null=True)
    bank_proof = models.FileField(upload_to='kyc/bank/', blank=True, null=True)
    
    # Address Details
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=6, blank=True, null=True)
    address_proof = models.FileField(upload_to='kyc/address/', blank=True, null=True)
    
    # API Response Data
    aadhaar_api_response = models.JSONField(blank=True, null=True)
    pan_api_response = models.JSONField(blank=True, null=True)
    bank_api_response = models.JSONField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='verified_kycs')
    rejection_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'kyc'
        verbose_name = 'KYC'
        verbose_name_plural = 'KYCs'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['aadhaar_number']),
            models.Index(fields=['pan_number']),
        ]
    
    def __str__(self):
        return f"KYC for {self.user.username}"
    
    def is_complete(self):
        return all([
            self.aadhaar_verified,
            self.pan_verified,
            self.bank_verified,
            self.aadhaar_number,
            self.pan_number,
            self.account_number,
        ])


class Document(TimestampedModel, SoftDeleteModel):
    """User documents for compliance"""
    
    DOCUMENT_TYPES = [
        ('aadhaar', 'Aadhaar Card'),
        ('pan', 'PAN Card'),
        ('bank', 'Bank Proof'),
        ('address', 'Address Proof'),
        ('photo', 'Photograph'),
        ('signature', 'Signature'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='documents/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="Size in bytes")
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['user', 'document_type']),
        ]
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.user.username}"


class AuditLog(TimestampedModel):
    """Audit log for compliance tracking"""
    
    ACTION_TYPES = [
        ('kyc_submit', 'KYC Submitted'),
        ('kyc_approve', 'KYC Approved'),
        ('kyc_reject', 'KYC Rejected'),
        ('document_upload', 'Document Uploaded'),
        ('document_delete', 'Document Deleted'),
        ('profile_update', 'Profile Updated'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('password_change', 'Password Changed'),
        ('other', 'Other Action'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.user.username if self.user else 'Unknown'}"