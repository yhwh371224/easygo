from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0007_backfill_post_regions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='region',
        ),
        migrations.AlterField(
            model_name='post',
            name='regions',
            field=models.ManyToManyField(blank=True, related_name='blog_posts', to='regions.region', verbose_name='Regions'),
        ),
    ]
