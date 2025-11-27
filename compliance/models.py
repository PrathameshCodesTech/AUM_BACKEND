# compliance/models.py
from django.db import models
from accounts.models import User, Organization, TimestampedModel

# ============================================
# KYC (Know Your Customer)
# ============================================


class KYC(TimestampedModel):
    """KYC verification for users"""

    DOCUMENT_TYPE_CHOICES = [
        ('aadhaar', 'Aadhaar Card'),
        ('pan', 'PAN Card'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('voter_id', 'Voter ID'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='kyc')
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='kyc_records')

    # Personal details
    full_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[(
        'male', 'Male'), ('female', 'Female'), ('other', 'Other')])

    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10)

    # Identity documents
    pan_number = models.CharField(max_length=10, blank=True)
    pan_document = models.FileField(
        upload_to='kyc/pan/', null=True, blank=True)

    aadhaar_number = models.CharField(max_length=12, blank=True)
    aadhaar_front = models.FileField(
        upload_to='kyc/aadhaar/', null=True, blank=True)
    aadhaar_back = models.FileField(
        upload_to='kyc/aadhaar/', null=True, blank=True)

    # Additional documents
    additional_document_type = models.CharField(
        max_length=20, choices=DOCUMENT_TYPE_CHOICES, blank=True)
    additional_document = models.FileField(
        upload_to='kyc/additional/', null=True, blank=True)

    # Photo
    photo = models.ImageField(upload_to='kyc/photos/', null=True, blank=True)

    # Bank details for payouts
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True)
    account_holder_name = models.CharField(max_length=255, blank=True)
    cancelled_cheque = models.FileField(
        upload_to='kyc/bank/', null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Review
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_kyc')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Expiry
    expires_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'kyc_records'
        verbose_name = 'KYC'
        verbose_name_plural = 'KYC Records'

    def __str__(self):
        return f"{self.user.username} - KYC ({self.status})"


# ============================================
# DOCUMENT MANAGEMENT
# ============================================
class Document(TimestampedModel):
    """Generic document storage"""

    DOCUMENT_CATEGORY_CHOICES = [
        ('agreement', 'Agreement'),
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('legal', 'Legal Document'),
        ('compliance', 'Compliance Document'),
        ('report', 'Report'),
        ('other', 'Other'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='documents')

    # Uploaded by
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')

    # Document details
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20, choices=DOCUMENT_CATEGORY_CHOICES)
    file = models.FileField(upload_to='documents/')
    file_size = models.BigIntegerField(help_text="in bytes")

    # Metadata
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    # Access control
    is_public = models.BooleanField(default=False)

    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['organization', 'category']),
        ]

    def __str__(self):
        return self.title


# ============================================
# AUDIT LOG
# ============================================
class AuditLog(models.Model):
    """Comprehensive audit trail for compliance"""

    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
        ('view', 'Viewed'),
        ('download', 'Downloaded'),
        ('payment', 'Payment'),
        ('other', 'Other'),
    ]

    # Who
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, related_name='audit_logs')

    # What
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    # investments, properties, users, etc.
    module = models.CharField(max_length=50)
    description = models.TextField()

    # Target (what was affected)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.IntegerField(null=True, blank=True)

    # Changes (JSON)
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)

    # When
    timestamp = models.DateTimeField(auto_now_add=True)

    # Where (IP, device)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['organization', 'timestamp']),
            models.Index(fields=['module', 'action']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action} - {self.module}"
