import django.db.models.deletion
import documents.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_document_property_alter_document_document_type_and_more'),
        ('investments', '0006_investmentpayment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentESignRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('surepass_client_id', models.CharField(blank=True, max_length=255)),
                ('surepass_sign_url', models.URLField(blank=True, max_length=1000)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('initiated', 'Initiated'),
                        ('signed', 'Signed'),
                        ('failed', 'Failed'),
                        ('expired', 'Expired'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('signed_file', models.FileField(
                    blank=True,
                    null=True,
                    upload_to=documents.models.esign_signed_upload_path,
                )),
                ('raw_init_payload', models.JSONField(blank=True, null=True)),
                ('raw_status_payload', models.JSONField(blank=True, null=True)),
                ('raw_signed_doc_payload', models.JSONField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='esign_requests',
                    to='documents.document',
                )),
                ('investment', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='esign_requests',
                    to='investments.investment',
                )),
                ('requested_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='esign_requests_sent',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('signed_document', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='signed_for_request',
                    to='documents.document',
                )),
                ('target_user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='esign_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
