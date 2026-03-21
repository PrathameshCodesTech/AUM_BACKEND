from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_identity_fields_esign'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentesignrequest',
            name='placement_mode',
            field=models.CharField(
                choices=[
                    ('single', 'Single Page'),
                    ('all_pages', 'All Pages'),
                    ('selected_pages', 'Selected Pages'),
                    ('manual', 'Manual Per Page'),
                ],
                default='single',
                help_text='How signature positions are distributed across pages',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='documentesignrequest',
            name='signature_positions',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Page \u2192 list of {x, y} dicts. E.g. {"1": [{"x": 10, "y": 20}]}',
            ),
        ),
        migrations.AddField(
            model_name='documentesignrequest',
            name='pdf_page_count',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='Number of pages in the document (detected at eSign creation time)',
            ),
        ),
    ]
