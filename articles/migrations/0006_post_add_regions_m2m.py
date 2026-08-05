from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0005_post_add_region'),
        ('regions', '0008_region_add_meta_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='regions',
            field=models.ManyToManyField(blank=True, related_name='blog_posts_m2m', to='regions.region', verbose_name='Regions'),
        ),
    ]
