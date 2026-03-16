from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0005_alter_aadhaarsession_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aadhaarsession',
            name='status',
            field=models.CharField(
                choices=[
                    ('initiated', 'Initiated'),
                    ('completed', 'Completed'),
                    ('failed', 'Failed'),
                    ('expired', 'Expired'),
                    ('needs_review', 'Needs Review'),
                    ('abandoned', 'Abandoned'),
                ],
                default='initiated',
                max_length=20,
            ),
        ),
    ]
