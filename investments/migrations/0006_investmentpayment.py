from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0005_investment_due_amount_investment_is_partial_payment_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InvestmentPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('payment_id', models.CharField(max_length=100, unique=True)),
                ('payment_number', models.PositiveIntegerField(default=2)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('due_amount_before', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('due_amount_after', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('payment_method', models.CharField(blank=True, choices=[('ONLINE','Online'),('POS','POS'),('DRAFT_CHEQUE','Draft / Cheque'),('NEFT_RTGS','NEFT / RTGS')], max_length=20)),
                ('payment_status', models.CharField(choices=[('PENDING','Pending'),('VERIFIED','Verified'),('FAILED','Failed'),('REFUNDED','Refunded')], default='PENDING', max_length=20)),
                ('payment_date', models.DateTimeField(blank=True, null=True)),
                ('payment_notes', models.TextField(blank=True)),
                ('payment_mode', models.CharField(blank=True, max_length=50)),
                ('transaction_no', models.CharField(blank=True, max_length=100, null=True)),
                ('pos_slip_image', models.ImageField(blank=True, null=True, upload_to='investments/pos_slips/%Y/%m/')),
                ('cheque_number', models.CharField(blank=True, max_length=50, null=True)),
                ('cheque_date', models.DateField(blank=True, null=True)),
                ('bank_name', models.CharField(blank=True, max_length=150, null=True)),
                ('ifsc_code', models.CharField(blank=True, max_length=20, null=True)),
                ('branch_name', models.CharField(blank=True, max_length=150, null=True)),
                ('cheque_image', models.ImageField(blank=True, null=True, upload_to='investments/cheques/%Y/%m/')),
                ('neft_rtgs_ref_no', models.CharField(blank=True, max_length=100, null=True)),
                ('payment_approved_at', models.DateTimeField(blank=True, null=True)),
                ('payment_rejection_reason', models.TextField(blank=True)),
                ('investment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instalment_payments', to='investments.investment')),
                ('payment_approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_instalments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'investment_payments',
                'ordering': ['payment_number', 'created_at'],
            },
        ),
    ]
