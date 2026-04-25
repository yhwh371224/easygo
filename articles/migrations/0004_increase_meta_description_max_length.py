from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0003_post_gmb_content_post_thumbnail_source_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='meta_description',
            field=models.CharField(blank=True, help_text='Displayed in Google search results (max 160 chars).', max_length=500, verbose_name='SEO Description'),
        ),
    ]
