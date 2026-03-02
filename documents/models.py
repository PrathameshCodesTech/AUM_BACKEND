from uuid import uuid4
from django.db import models
from django.conf import settings
from accounts.models import TimestampedModel


def document_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
    return f"documents/{instance.document_type.lower()}/{uuid4().hex}.{ext}"


class Document(TimestampedModel):
    COMMON = 'COMMON'
    PROJECT = 'PROJECT'
    TYPE_CHOICES = [
        (COMMON, 'Common'),
        (PROJECT, 'Project'),
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
    # Empty = visible to all (COMMON); non-empty = visible only to selected users (PROJECT)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='project_docs',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.document_type})"
