from django.db import migrations, models

MELBOURNE_META_TITLE = (
    "Melbourne Airport Transfer | Fixed Price & Private (8-13 Seater) | EasyGo"
)
MELBOURNE_META_DESCRIPTION = (
    "Book your Melbourne airport transfer now! Private pickup service with 8-13 seater vehicles. "
    "Serving Melbourne CBD, Northern Suburbs & Western Melbourne. Fixed prices, no hidden fees. Available 24/7"
)


def seed_meta(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    Region.objects.filter(slug='melbourne').update(
        meta_title=MELBOURNE_META_TITLE,
        meta_description=MELBOURNE_META_DESCRIPTION,
    )


def reverse_meta(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    Region.objects.filter(slug='melbourne').update(
        meta_title='',
        meta_description='',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0007_seed_melbourne_guides'),
    ]

    operations = [
        migrations.AddField(
            model_name='region',
            name='meta_title',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunPython(seed_meta, reverse_meta),
    ]
