from uuid import uuid4
from django.db import models
from django.conf import settings
from accounts.models import TimestampedModel


def document_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
    return f"documents/{instance.document_type.lower()}/{uuid4().hex}.{ext}"


class Document(TimestampedModel):
    COMMON = 'COMMON'
    INDIVIDUAL = 'INDIVIDUAL'
    PROPERTY = 'PROPERTY'
    TYPE_CHOICES = [
        (COMMON, 'Common'),
        (INDIVIDUAL, 'Individual'),
        (PROPERTY, 'Property'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=document_upload_path)
    document_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=COMMON)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_docs',
    )
    # INDIVIDUAL type: visible only to these selected users
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='individual_docs',
    )
    # PROPERTY type: visible to all investors of this property
    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='storage_documents',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.document_type})"


def esign_signed_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'pdf'
    return f"documents/esign/signed/{uuid4().hex}.{ext}"


class DocumentESignRequest(TimestampedModel):
    """
    Tracks an admin-initiated eSign request for a specific user and document.

    Identity check lifecycle:
      - identity_check_status='not_checked'  : not yet evaluated
      - identity_check_status='verified'     : provider returned signer name that matches KYC/profile
      - identity_check_status='unverified'   : provider gave no signer identity; document is 'signed'
                                               but identity was NOT strongly validated
      - identity_check_status='mismatch'     : provider returned a name that does NOT match → status='needs_review'
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('signed', 'Signed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
        ('needs_review', 'Needs Review'),       # signed but identity mismatch or unresolvable
        ('identity_mismatch', 'Identity Mismatch'),  # explicit hard mismatch
    ]

    IDENTITY_CHECK_CHOICES = [
        ('not_checked', 'Not Checked'),
        ('verified', 'Verified'),
        ('unverified', 'Unverified'),      # provider gave no identity info
        ('mismatch', 'Mismatch'),          # provider name does not match KYC
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='esign_requests'
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='esign_requests'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='esign_requests_sent'
    )
    investment = models.ForeignKey(
        'investments.Investment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='esign_requests'
    )

    surepass_client_id = models.CharField(max_length=255, blank=True)
    surepass_sign_url = models.URLField(max_length=1000, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    signed_file = models.FileField(upload_to=esign_signed_upload_path, null=True, blank=True)
    signed_document = models.OneToOneField(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signed_for_request'
    )

    raw_init_payload = models.JSONField(blank=True, null=True)
    raw_status_payload = models.JSONField(blank=True, null=True)
    raw_signed_doc_payload = models.JSONField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    # Identity verification fields — populated during eSign refresh
    signer_name_returned = models.CharField(
        max_length=255, blank=True,
        help_text="Signer name returned by the eSign provider (if any)"
    )
    identity_check_status = models.CharField(
        max_length=20, choices=IDENTITY_CHECK_CHOICES, default='not_checked',
        help_text="Result of comparing provider signer identity against KYC/profile"
    )
    identity_mismatch_reason = models.TextField(
        blank=True,
        help_text="Explanation when identity_check_status is mismatch or unverified"
    )

    # Signature placement fields — configurable by admin at eSign creation time
    PLACEMENT_MODE_CHOICES = [
        ('single', 'Single Page'),
        ('all_pages', 'All Pages'),
        ('selected_pages', 'Selected Pages'),
        ('manual', 'Manual Per Page'),
    ]
    placement_mode = models.CharField(
        max_length=20, choices=PLACEMENT_MODE_CHOICES, default='single',
        help_text='How signature positions are distributed across pages'
    )
    signature_positions = models.JSONField(
        default=dict, blank=True,
        help_text='Page → list of {x, y} dicts. E.g. {"1": [{"x": 10, "y": 20}]}'
    )
    pdf_page_count = models.IntegerField(
        null=True, blank=True,
        help_text='Number of pages in the document (detected at eSign creation time)'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"eSign {self.id} — {self.document.title} → {self.target_user}"
