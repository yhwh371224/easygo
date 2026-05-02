from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

BRISBANE_SUBURBS = {
    # Inner City (~10-18 km from BNE)
    "Brisbane CBD":         {'price': 80,  'zone': 'Inner City'},
    "Spring Hill":          {'price': 80,  'zone': 'Inner City'},
    "Fortitude Valley":     {'price': 80,  'zone': 'Inner City'},
    "New Farm":             {'price': 82,  'zone': 'Inner City'},
    "Newstead":             {'price': 80,  'zone': 'Inner City'},
    "Teneriffe":            {'price': 82,  'zone': 'Inner City'},
    "South Brisbane":       {'price': 82,  'zone': 'Inner City'},
    "West End":             {'price': 82,  'zone': 'Inner City'},
    "Kangaroo Point":       {'price': 82,  'zone': 'Inner City'},
    "Woolloongabba":        {'price': 85,  'zone': 'Inner City'},
    "Highgate Hill":        {'price': 85,  'zone': 'Inner City'},
    "Dutton Park":          {'price': 85,  'zone': 'Inner City'},

    # Inner North (~15-25 km)
    "Clayfield":            {'price': 75,  'zone': 'Inner North'},
    "Ascot":                {'price': 75,  'zone': 'Inner North'},
    "Hamilton":             {'price': 75,  'zone': 'Inner North'},
    "Hendra":               {'price': 75,  'zone': 'Inner North'},
    "Nundah":               {'price': 80,  'zone': 'Inner North'},
    "Wavell Heights":       {'price': 82,  'zone': 'Inner North'},
    "Windsor":              {'price': 82,  'zone': 'Inner North'},
    "Gordon Park":          {'price': 82,  'zone': 'Inner North'},
    "Stafford":             {'price': 85,  'zone': 'Inner North'},
    "Kedron":               {'price': 85,  'zone': 'Inner North'},
    "Chermside":            {'price': 85,  'zone': 'Inner North'},
    "Albion":               {'price': 80,  'zone': 'Inner North'},

    # Inner South (~18-28 km)
    "Annerley":             {'price': 88,  'zone': 'Inner South'},
    "Fairfield":            {'price': 88,  'zone': 'Inner South'},
    "Greenslopes":          {'price': 88,  'zone': 'Inner South'},
    "Moorooka":             {'price': 90,  'zone': 'Inner South'},
    "Rocklea":              {'price': 92,  'zone': 'Inner South'},
    "Nathan":               {'price': 92,  'zone': 'Inner South'},
    "MacGregor":            {'price': 95,  'zone': 'Inner South'},
    "Robertson":            {'price': 95,  'zone': 'Inner South'},
    "Salisbury":            {'price': 92,  'zone': 'Inner South'},
    "Tarragindi":           {'price': 92,  'zone': 'Inner South'},

    # Inner West (~20-32 km)
    "Milton":               {'price': 82,  'zone': 'Inner West'},
    "Auchenflower":         {'price': 85,  'zone': 'Inner West'},
    "Paddington":           {'price': 85,  'zone': 'Inner West'},
    "Rosalie":              {'price': 85,  'zone': 'Inner West'},
    "Kelvin Grove":         {'price': 85,  'zone': 'Inner West'},
    "Red Hill":             {'price': 85,  'zone': 'Inner West'},
    "Ashgrove":             {'price': 90,  'zone': 'Inner West'},
    "Bardon":               {'price': 92,  'zone': 'Inner West'},
    "Enoggera":             {'price': 90,  'zone': 'Inner West'},
    "Gaythorne":            {'price': 92,  'zone': 'Inner West'},
    "Mitchelton":           {'price': 92,  'zone': 'Inner West'},
    "Keperra":              {'price': 95,  'zone': 'Inner West'},
    "Alderley":             {'price': 88,  'zone': 'Inner West'},

    # Inner East (~18-28 km)
    "Morningside":          {'price': 88,  'zone': 'Inner East'},
    "Hawthorne":            {'price': 88,  'zone': 'Inner East'},
    "Balmoral":             {'price': 90,  'zone': 'Inner East'},
    "Norman Park":          {'price': 88,  'zone': 'Inner East'},
    "Camp Hill":            {'price': 90,  'zone': 'Inner East'},
    "Carina":               {'price': 92,  'zone': 'Inner East'},
    "Carindale":            {'price': 95,  'zone': 'Inner East'},
    "Cannon Hill":          {'price': 88,  'zone': 'Inner East'},
    "Tingalpa":             {'price': 90,  'zone': 'Inner East'},
    "Bulimba":              {'price': 88,  'zone': 'Inner East'},
    "Murarrie":             {'price': 82,  'zone': 'Inner East'},

    # Northern Suburbs (~28-45 km)
    "Virginia":             {'price': 80,  'zone': 'Northern Suburbs'},
    "Northgate":            {'price': 78,  'zone': 'Northern Suburbs'},
    "Banyo":                {'price': 78,  'zone': 'Northern Suburbs'},
    "Geebung":              {'price': 88,  'zone': 'Northern Suburbs'},
    "Zillmere":             {'price': 90,  'zone': 'Northern Suburbs'},
    "Boondall":             {'price': 85,  'zone': 'Northern Suburbs'},
    "Bracken Ridge":        {'price': 92,  'zone': 'Northern Suburbs'},
    "Sandgate":             {'price': 95,  'zone': 'Northern Suburbs'},
    "Brighton":             {'price': 98,  'zone': 'Northern Suburbs'},
    "Deagon":               {'price': 92,  'zone': 'Northern Suburbs'},
    "Shorncliffe":          {'price': 98,  'zone': 'Northern Suburbs'},
    "Fitzgibbon":           {'price': 90,  'zone': 'Northern Suburbs'},
    "Carseldine":           {'price': 92,  'zone': 'Northern Suburbs'},
    "Aspley":               {'price': 90,  'zone': 'Northern Suburbs'},
    "Bridgeman Downs":      {'price': 95,  'zone': 'Northern Suburbs'},
    "McDowall":             {'price': 92,  'zone': 'Northern Suburbs'},
    "Taigum":               {'price': 88,  'zone': 'Northern Suburbs'},
    "Bald Hills":           {'price': 95,  'zone': 'Northern Suburbs'},

    # Western Suburbs (~28-45 km)
    "Toowong":              {'price': 90,  'zone': 'Western Suburbs'},
    "Taringa":              {'price': 92,  'zone': 'Western Suburbs'},
    "St Lucia":             {'price': 90,  'zone': 'Western Suburbs'},
    "Indooroopilly":        {'price': 95,  'zone': 'Western Suburbs'},
    "Chapel Hill":          {'price': 100, 'zone': 'Western Suburbs'},
    "Kenmore":              {'price': 102, 'zone': 'Western Suburbs'},
    "Kenmore Hills":        {'price': 105, 'zone': 'Western Suburbs'},
    "Brookfield":           {'price': 110, 'zone': 'Western Suburbs'},
    "The Gap":              {'price': 100, 'zone': 'Western Suburbs'},
    "Ferny Hills":          {'price': 102, 'zone': 'Western Suburbs'},
    "Arana Hills":          {'price': 100, 'zone': 'Western Suburbs'},
    "Ferny Grove":          {'price': 105, 'zone': 'Western Suburbs'},
    "Upper Kedron":         {'price': 105, 'zone': 'Western Suburbs'},

    # South-Eastern Suburbs (~35-50 km)
    "Sunnybank":            {'price': 98,  'zone': 'South-Eastern Suburbs'},
    "Sunnybank Hills":      {'price': 100, 'zone': 'South-Eastern Suburbs'},
    "Runcorn":              {'price': 100, 'zone': 'South-Eastern Suburbs'},
    "Calamvale":            {'price': 105, 'zone': 'South-Eastern Suburbs'},
    "Stretton":             {'price': 108, 'zone': 'South-Eastern Suburbs'},
    "Acacia Ridge":         {'price': 98,  'zone': 'South-Eastern Suburbs'},
    "Coopers Plains":       {'price': 95,  'zone': 'South-Eastern Suburbs'},
    "Archerfield":          {'price': 95,  'zone': 'South-Eastern Suburbs'},
    "Eight Mile Plains":    {'price': 102, 'zone': 'South-Eastern Suburbs'},
    "Kuraby":               {'price': 105, 'zone': 'South-Eastern Suburbs'},
    "Wishart":              {'price': 100, 'zone': 'South-Eastern Suburbs'},
    "Mount Gravatt":        {'price': 95,  'zone': 'South-Eastern Suburbs'},
    "Mount Gravatt East":   {'price': 95,  'zone': 'South-Eastern Suburbs'},
    "Upper Mount Gravatt":  {'price': 98,  'zone': 'South-Eastern Suburbs'},

    # Far North (~50-70 km)
    "Kallangur":            {'price': 110, 'zone': 'Far North'},
    "Dakabin":              {'price': 112, 'zone': 'Far North'},
    "Narangba":             {'price': 115, 'zone': 'Far North'},
    "Mango Hill":           {'price': 112, 'zone': 'Far North'},
    "North Lakes":          {'price': 115, 'zone': 'Far North'},
    "Griffin":              {'price': 115, 'zone': 'Far North'},
    "Deception Bay":        {'price': 118, 'zone': 'Far North'},
    "Morayfield":           {'price': 122, 'zone': 'Far North'},
    "Caboolture":           {'price': 130, 'zone': 'Far North'},

    # Far South (~50-70 km)
    "Springwood":           {'price': 115, 'zone': 'Far South'},
    "Shailer Park":         {'price': 118, 'zone': 'Far South'},
    "Loganholme":           {'price': 120, 'zone': 'Far South'},
    "Rochedale":            {'price': 112, 'zone': 'Far South'},
    "Meadowbrook":          {'price': 120, 'zone': 'Far South'},
    "Kingston":             {'price': 122, 'zone': 'Far South'},
    "Slacks Creek":         {'price': 118, 'zone': 'Far South'},
    "Woodridge":            {'price': 120, 'zone': 'Far South'},
    "Underwood":            {'price': 112, 'zone': 'Far South'},

    # Ipswich Corridor (~45-60 km west)
    "Wacol":                {'price': 105, 'zone': 'Ipswich Corridor'},
    "Darra":                {'price': 100, 'zone': 'Ipswich Corridor'},
    "Oxley":                {'price': 100, 'zone': 'Ipswich Corridor'},
    "Corinda":              {'price': 100, 'zone': 'Ipswich Corridor'},
    "Sherwood":             {'price': 98,  'zone': 'Ipswich Corridor'},
    "Graceville":           {'price': 98,  'zone': 'Ipswich Corridor'},
    "Chelmer":              {'price': 98,  'zone': 'Ipswich Corridor'},
    "Seventeen Mile Rocks": {'price': 105, 'zone': 'Ipswich Corridor'},
    "Sinnamon Park":        {'price': 100, 'zone': 'Ipswich Corridor'},
    "Jindalee":             {'price': 102, 'zone': 'Ipswich Corridor'},
    "Middle Park":          {'price': 105, 'zone': 'Ipswich Corridor'},
    "Riverhills":           {'price': 108, 'zone': 'Ipswich Corridor'},
}

# Pinned items appear at the top of the booking dropdown
PINNED = {
    "Brisbane Airport": 0,
}

# Airport/terminal entries (no pillar page needed)
EXTRA_PINNED = [
    {"name": "Brisbane Airport", "price": 0, "zone": "Inner North"},
]


class Command(BaseCommand):
    help = 'Import Brisbane suburbs into RegionSuburb. Idempotent — safe to re-run.'

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        try:
            brisbane = Region.objects.get(slug='brisbane')
        except Region.DoesNotExist:
            self.stderr.write(self.style.ERROR("Brisbane region not found. Create it first."))
            return

        created_count = 0
        updated_count = 0

        for name, data in BRISBANE_SUBURBS.items():
            slug = slugify(name)
            price = Decimal(str(data['price']))
            zone = data['zone']

            obj, was_created = RegionSuburb.objects.update_or_create(
                region=brisbane,
                slug=slug,
                defaults={
                    'name': name,
                    'price': price,
                    'zone': zone,
                    'is_active': True,
                    'is_pinned': name in PINNED,
                    'sort_order': PINNED.get(name, 0),
                    'meta_title': f"{name} Airport Shuttle | EasyGo Brisbane",
                    'meta_description': (
                        f"Private airport shuttle from {name} to Brisbane Airport (BNE). "
                        f"Fixed price from ${int(price)} per vehicle. "
                        "Door-to-door service. Book online."
                    ),
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        for item in EXTRA_PINNED:
            name = item['name']
            slug = slugify(name)

            obj, was_created = RegionSuburb.objects.update_or_create(
                region=brisbane,
                slug=slug,
                defaults={
                    'name': name,
                    'price': Decimal('0'),
                    'zone': item['zone'],
                    'is_active': True,
                    'is_pinned': True,
                    'sort_order': PINNED[name],
                    'meta_title': f"{name} | EasyGo Brisbane",
                    'meta_description': '',
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created: {created_count}, Updated: {updated_count}'
        ))
