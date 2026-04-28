from django.db import migrations


PINNED_ENTRIES = [
    {
        'name': 'Pickup from International Airport',
        'slug': 'pickup-from-international-airport',
        'zone': 'Airport',
        'sort_order': 0,
    },
    {
        'name': 'Pickup from Domestic Airport',
        'slug': 'pickup-from-domestic-airport',
        'zone': 'Airport',
        'sort_order': 1,
    },
    {
        'name': 'Drop off to International Airport',
        'slug': 'drop-off-to-international-airport',
        'zone': 'Airport',
        'sort_order': 2,
    },
    {
        'name': 'Drop off to Domestic Airport',
        'slug': 'drop-off-to-domestic-airport',
        'zone': 'Airport',
        'sort_order': 3,
    },
]


def add_pinned_entries(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    RegionSuburb = apps.get_model('regions', 'RegionSuburb')
    try:
        melbourne = Region.objects.get(slug='melbourne')
    except Region.DoesNotExist:
        return
    for entry in PINNED_ENTRIES:
        RegionSuburb.objects.get_or_create(
            region=melbourne,
            slug=entry['slug'],
            defaults={
                'name': entry['name'],
                'price': '0.00',
                'zone': entry['zone'],
                'is_active': True,
                'is_pinned': True,
                'sort_order': entry['sort_order'],
            },
        )


def remove_pinned_entries(apps, schema_editor):
    RegionSuburb = apps.get_model('regions', 'RegionSuburb')
    slugs = [e['slug'] for e in PINNED_ENTRIES]
    RegionSuburb.objects.filter(region__slug='melbourne', slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0010_remove_featured_fields'),
    ]

    operations = [
        migrations.RunPython(add_pinned_entries, remove_pinned_entries),
    ]
