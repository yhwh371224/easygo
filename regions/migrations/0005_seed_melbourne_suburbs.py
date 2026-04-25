from decimal import Decimal
from django.db import migrations


MELBOURNE_SUBURBS = [
    # Inner North/West — closest to Melbourne Airport (~12-18 km)
    {'name': 'Essendon',          'slug': 'essendon',          'price': '62.00', 'zone': 'Inner North/West'},
    {'name': 'Moonee Ponds',      'slug': 'moonee-ponds',      'price': '65.00', 'zone': 'Inner North/West'},

    # Central Melbourne (~22-28 km)
    {'name': 'Melbourne CBD',     'slug': 'cbd',               'price': '75.00', 'zone': 'Central Melbourne'},
    {'name': 'Southbank',         'slug': 'southbank',         'price': '75.00', 'zone': 'Central Melbourne'},
    {'name': 'Carlton',           'slug': 'carlton',           'price': '75.00', 'zone': 'Central Melbourne'},
    {'name': 'Fitzroy',           'slug': 'fitzroy',           'price': '76.00', 'zone': 'Central Melbourne'},
    {'name': 'Richmond',          'slug': 'richmond',          'price': '78.00', 'zone': 'Central Melbourne'},
    {'name': 'Coburg',            'slug': 'coburg',            'price': '72.00', 'zone': 'Central Melbourne'},
    {'name': 'Brunswick',         'slug': 'brunswick',         'price': '75.00', 'zone': 'Central Melbourne'},

    # Inner North (~25-32 km)
    {'name': 'Northcote',         'slug': 'northcote',         'price': '78.00', 'zone': 'Inner North'},
    {'name': 'Preston',           'slug': 'preston',           'price': '78.00', 'zone': 'Inner North'},
    {'name': 'Reservoir',         'slug': 'reservoir',         'price': '76.00', 'zone': 'Inner North'},
    {'name': 'Ivanhoe',           'slug': 'ivanhoe',           'price': '82.00', 'zone': 'Inner North'},
    {'name': 'Heidelberg',        'slug': 'heidelberg',        'price': '82.00', 'zone': 'Inner North'},

    # Inner South (~27-33 km)
    {'name': 'South Yarra',       'slug': 'south-yarra',       'price': '82.00', 'zone': 'Inner South'},
    {'name': 'Prahran',           'slug': 'prahran',           'price': '82.00', 'zone': 'Inner South'},
    {'name': 'Windsor',           'slug': 'windsor',           'price': '82.00', 'zone': 'Inner South'},
    {'name': 'St Kilda',          'slug': 'st-kilda',          'price': '85.00', 'zone': 'Inner South'},
    {'name': 'Brighton',          'slug': 'brighton',          'price': '88.00', 'zone': 'Inner South'},

    # Inner East (~30-35 km)
    {'name': 'Toorak',            'slug': 'toorak',            'price': '88.00', 'zone': 'Inner East'},
    {'name': 'Hawthorn',          'slug': 'hawthorn',          'price': '85.00', 'zone': 'Inner East'},
    {'name': 'Camberwell',        'slug': 'camberwell',        'price': '90.00', 'zone': 'Inner East'},
    {'name': 'Oakleigh',          'slug': 'oakleigh',          'price': '88.00', 'zone': 'Inner East'},

    # Eastern Suburbs (~33-55 km)
    {'name': 'Doncaster',         'slug': 'doncaster',         'price': '90.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Box Hill',          'slug': 'box-hill',          'price': '92.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Glen Waverley',     'slug': 'glen-waverley',     'price': '90.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Greensborough',     'slug': 'greensborough',     'price': '90.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Eltham',            'slug': 'eltham',            'price': '92.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Diamond Creek',     'slug': 'diamond-creek',     'price': '98.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Ringwood',          'slug': 'ringwood',          'price': '95.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Croydon',           'slug': 'croydon',           'price': '95.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Bayswater',         'slug': 'bayswater',         'price': '102.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Boronia',           'slug': 'boronia',           'price': '102.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Mooroolbark',       'slug': 'mooroolbark',       'price': '105.00', 'zone': 'Eastern Suburbs'},
    {'name': 'Lilydale',          'slug': 'lilydale',          'price': '110.00', 'zone': 'Eastern Suburbs'},

    # Northern Suburbs (~28-42 km)
    {'name': 'Craigieburn',       'slug': 'craigieburn',       'price': '72.00', 'zone': 'Northern Suburbs'},
    {'name': 'Roxburgh Park',     'slug': 'roxburgh-park',     'price': '70.00', 'zone': 'Northern Suburbs'},
    {'name': 'Bundoora',          'slug': 'bundoora',          'price': '85.00', 'zone': 'Northern Suburbs'},
    {'name': 'Epping',            'slug': 'epping',            'price': '85.00', 'zone': 'Northern Suburbs'},
    {'name': 'Mill Park',         'slug': 'mill-park',         'price': '88.00', 'zone': 'Northern Suburbs'},
    {'name': 'South Morang',      'slug': 'south-morang',      'price': '90.00', 'zone': 'Northern Suburbs'},

    # Western Suburbs (~25-42 km)
    {'name': 'Footscray',         'slug': 'footscray',         'price': '78.00', 'zone': 'Western Suburbs'},
    {'name': 'Williamstown',      'slug': 'williamstown',      'price': '82.00', 'zone': 'Western Suburbs'},
    {'name': 'Altona',            'slug': 'altona',            'price': '82.00', 'zone': 'Western Suburbs'},
    {'name': 'Laverton',          'slug': 'laverton',          'price': '85.00', 'zone': 'Western Suburbs'},
    {'name': 'Point Cook',        'slug': 'point-cook',        'price': '90.00', 'zone': 'Western Suburbs'},
    {'name': 'Hoppers Crossing',  'slug': 'hoppers-crossing',  'price': '92.00', 'zone': 'Western Suburbs'},
    {'name': 'Werribee',          'slug': 'werribee',          'price': '92.00', 'zone': 'Western Suburbs'},

    # South-East (~45-58 km)
    {'name': 'Knox',              'slug': 'knox',              'price': '105.00', 'zone': 'South-East'},
    {'name': 'Springvale',        'slug': 'springvale',        'price': '105.00', 'zone': 'South-East'},
    {'name': 'Dandenong',         'slug': 'dandenong',         'price': '108.00', 'zone': 'South-East'},
    {'name': 'Frankston',         'slug': 'frankston',         'price': '115.00', 'zone': 'South-East'},

    # Regional (65 km+)
    {'name': 'Mornington',        'slug': 'mornington',        'price': '155.00', 'zone': 'Regional'},
    {'name': 'Geelong',           'slug': 'geelong',           'price': '165.00', 'zone': 'Regional'},
]


def seed_melbourne_suburbs(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    RegionSuburb = apps.get_model('regions', 'RegionSuburb')

    try:
        melbourne = Region.objects.get(slug='melbourne')
    except Region.DoesNotExist:
        return

    for s in MELBOURNE_SUBURBS:
        price_display = int(Decimal(s['price']))
        RegionSuburb.objects.get_or_create(
            region=melbourne,
            slug=s['slug'],
            defaults={
                'name': s['name'],
                'price': Decimal(s['price']),
                'zone': s['zone'],
                'is_active': True,
                'meta_title': f"{s['name']} Airport Shuttle | EasyGo Melbourne",
                'meta_description': (
                    f"Private airport shuttle from {s['name']} to Melbourne Airport (MEL). "
                    f"Fixed price from ${price_display} per vehicle. "
                    "Door-to-door, meet & greet, flight tracking included. Book online."
                ),
            },
        )


def unseed_melbourne_suburbs(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    RegionSuburb = apps.get_model('regions', 'RegionSuburb')
    try:
        melbourne = Region.objects.get(slug='melbourne')
        slugs = [s['slug'] for s in MELBOURNE_SUBURBS]
        RegionSuburb.objects.filter(region=melbourne, slug__in=slugs).delete()
    except Region.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0004_update_melbourne_phone'),
    ]

    operations = [
        migrations.RunPython(seed_melbourne_suburbs, reverse_code=unseed_melbourne_suburbs),
    ]
