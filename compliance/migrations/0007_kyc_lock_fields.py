from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0006_aadhaarsession_needs_review_abandoned'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Aadhaar review / lock fields
        migrations.AddField(
            model_name='kyc',
            name='aadhaar_review_status',
            field=models.CharField(
                choices=[
                    ('not_started', 'Not Started'),
                    ('submitted', 'Submitted'),
                    ('verified_unlocked', 'Verified (Unlocked)'),
                    ('approved_locked', 'Approved & Locked'),
                    ('rejected', 'Rejected'),
                    ('needs_retry', 'Needs Retry'),
                ],
                default='not_started',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='kyc',
            name='aadhaar_locked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='kyc',
            name='aadhaar_locked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kyc',
            name='aadhaar_locked_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='aadhaar_locked_kycs',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='kyc',
            name='aadhaar_review_note',
            field=models.TextField(blank=True),
        ),
        # PAN review / lock fields
        migrations.AddField(
            model_name='kyc',
            name='pan_review_status',
            field=models.CharField(
                choices=[
                    ('not_started', 'Not Started'),
                    ('submitted', 'Submitted'),
                    ('verified_unlocked', 'Verified (Unlocked)'),
                    ('approved_locked', 'Approved & Locked'),
                    ('rejected', 'Rejected'),
                    ('needs_retry', 'Needs Retry'),
                ],
                default='not_started',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='kyc',
            name='pan_locked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='kyc',
            name='pan_locked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kyc',
            name='pan_locked_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pan_locked_kycs',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='kyc',
            name='pan_review_note',
            field=models.TextField(blank=True),
        ),
    ]
