from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_user_legal_full_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='middle_name',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
    ]
