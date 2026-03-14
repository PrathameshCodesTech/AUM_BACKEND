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
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('signed', 'Signed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
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

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"eSign {self.id} — {self.document.title} → {self.target_user}"
