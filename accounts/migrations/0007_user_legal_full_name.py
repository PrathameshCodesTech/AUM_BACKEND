from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_otpverification'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='legal_full_name',
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text='Full name exactly as on government ID (used for KYC matching)',
            ),
        ),
    ]
