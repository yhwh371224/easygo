from django.db import migrations


REGION_DATA = [
    {
        'slug': 'melbourne',
        'name': 'Melbourne',
        'airport_code': 'MEL',
        'timezone': 'Australia/Melbourne',
        'phone': '03 9999 9999',
    },
    {
        'slug': 'brisbane',
        'name': 'Brisbane',
        'airport_code': 'BNE',
        'timezone': 'Australia/Brisbane',
        'phone': '07 9999 9999',
    },
    {
        'slug': 'adelaide',
        'name': 'Adelaide',
        'airport_code': 'ADL',
        'timezone': 'Australia/Adelaide',
        'phone': '08 9999 9999',
    },
    {
        'slug': 'perth',
        'name': 'Perth',
        'airport_code': 'PER',
        'timezone': 'Australia/Perth',
        'phone': '08 9999 9998',
    },
    {
        'slug': 'gold-coast',
        'name': 'Gold Coast',
        'airport_code': 'OOL',
        'timezone': 'Australia/Brisbane',
        'phone': '07 9999 9998',
    },
]


def seed_regions(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    for data in REGION_DATA:
        Region.objects.get_or_create(slug=data['slug'], defaults=data)


def unseed_regions(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    slugs = [d['slug'] for d in REGION_DATA]
    Region.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_regions, reverse_code=unseed_regions),
    ]
