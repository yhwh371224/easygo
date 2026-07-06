from django.db import migrations, models


def backfill_driver_price(apps, schema_editor):
    Post = apps.get_model('blog', 'Post')
    Post.objects.filter(driver_price__isnull=True).update(driver_price=models.F('price'))
    Post.objects.filter(driver_price='').update(driver_price=models.F('price'))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0041_post_driver_price'),
    ]

    operations = [
        migrations.RunPython(backfill_driver_price, noop),
    ]
