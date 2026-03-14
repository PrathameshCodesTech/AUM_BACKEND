import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0003_kyc_dob_validation_status_kyc_name_match_score_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # New PAN fields
        migrations.AddField(
            model_name='kyc',
            name='pan_gender',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='kyc',
            name='pan_masked_aadhaar',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        # AadhaarSession model
        migrations.CreateModel(
            name='AadhaarSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client_id', models.CharField(max_length=255, unique=True)),
                ('reference_id', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(
                    choices=[
                        ('initiated', 'Initiated'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                        ('expired', 'Expired'),
                    ],
                    default='initiated',
                    max_length=20,
                )),
                ('raw_init_payload', models.JSONField(blank=True, null=True)),
                ('raw_result_payload', models.JSONField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='aadhaar_sessions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'aadhaar_sessions',
                'ordering': ['-created_at'],
            },
        ),
    ]
