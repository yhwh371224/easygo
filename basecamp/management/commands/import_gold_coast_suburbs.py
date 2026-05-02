from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

# OOL (Coolangatta Airport) is at the southern tip of the Gold Coast.
# Zones are ordered by distance from OOL — south/closest first, north/furthest last.
# Hinterland suburbs run inland (west) and are priced by road distance.

GOLD_COAST_SUBURBS = {
    # Airport Surrounds — 0-10 km from OOL
    "Coolangatta":          {'price': 55,  'zone': 'Airport Surrounds'},
    "Kirra":                {'price': 55,  'zone': 'Airport Surrounds'},
    "Bilinga":              {'price': 55,  'zone': 'Airport Surrounds'},
    "Tugun":                {'price': 60,  'zone': 'Airport Surrounds'},
    "Currumbin":            {'price': 62,  'zone': 'Airport Surrounds'},
    "Currumbin Waters":     {'price': 65,  'zone': 'Airport Surrounds'},
    # Tweed Heads (NSW) — cross-border, close to OOL
    "Tweed Heads":          {'price': 65,  'zone': 'Airport Surrounds'},
    "Tweed Heads South":    {'price': 62,  'zone': 'Airport Surrounds'},
    "Tweed Heads West":     {'price': 68,  'zone': 'Airport Surrounds'},
    "Banora Point":         {'price': 65,  'zone': 'Airport Surrounds'},
    "Bilambil Heights":     {'price': 70,  'zone': 'Airport Surrounds'},

    # Southern Gold Coast — 10-22 km from OOL
    "Palm Beach":           {'price': 68,  'zone': 'Southern Gold Coast'},
    "Elanora":              {'price': 70,  'zone': 'Southern Gold Coast'},
    "Tallebudgera":         {'price': 72,  'zone': 'Southern Gold Coast'},
    "Tallebudgera Valley":  {'price': 78,  'zone': 'Southern Gold Coast'},
    "Burleigh Heads":       {'price': 75,  'zone': 'Southern Gold Coast'},
    "Burleigh Waters":      {'price': 78,  'zone': 'Southern Gold Coast'},
    "West Burleigh":        {'price': 78,  'zone': 'Southern Gold Coast'},
    "Miami":                {'price': 80,  'zone': 'Southern Gold Coast'},
    "Nobby Beach":          {'price': 80,  'zone': 'Southern Gold Coast'},

    # Central Gold Coast — 22-32 km from OOL
    "Mermaid Beach":        {'price': 82,  'zone': 'Central Gold Coast'},
    "Mermaid Waters":       {'price': 82,  'zone': 'Central Gold Coast'},
    "Broadbeach":           {'price': 85,  'zone': 'Central Gold Coast'},
    "Broadbeach Waters":    {'price': 85,  'zone': 'Central Gold Coast'},
    "Surfers Paradise":     {'price': 88,  'zone': 'Central Gold Coast'},
    "Isle of Capri":        {'price': 88,  'zone': 'Central Gold Coast'},
    "Chevron Island":       {'price': 88,  'zone': 'Central Gold Coast'},
    "Bundall":              {'price': 88,  'zone': 'Central Gold Coast'},
    "Benowa":               {'price': 90,  'zone': 'Central Gold Coast'},
    "Ashmore":              {'price': 90,  'zone': 'Central Gold Coast'},
    "Carrara":              {'price': 88,  'zone': 'Central Gold Coast'},

    # Northern Gold Coast — 32-45 km from OOL
    "Main Beach":           {'price': 92,  'zone': 'Northern Gold Coast'},
    "Southport":            {'price': 95,  'zone': 'Northern Gold Coast'},
    "Labrador":             {'price': 95,  'zone': 'Northern Gold Coast'},
    "Biggera Waters":       {'price': 95,  'zone': 'Northern Gold Coast'},
    "Hollywell":            {'price': 98,  'zone': 'Northern Gold Coast'},
    "Runaway Bay":          {'price': 98,  'zone': 'Northern Gold Coast'},
    "Paradise Point":       {'price': 100, 'zone': 'Northern Gold Coast'},
    "Coombabah":            {'price': 98,  'zone': 'Northern Gold Coast'},
    "Arundel":              {'price': 95,  'zone': 'Northern Gold Coast'},
    "Molendinar":           {'price': 95,  'zone': 'Northern Gold Coast'},
    "Parkwood":             {'price': 95,  'zone': 'Northern Gold Coast'},
    "Nerang":               {'price': 92,  'zone': 'Northern Gold Coast'},
    "Highland Park":        {'price': 92,  'zone': 'Northern Gold Coast'},

    # Far North — 45-65 km from OOL
    "Helensvale":           {'price': 105, 'zone': 'Far North'},
    "Hope Island":          {'price': 105, 'zone': 'Far North'},
    "Sanctuary Cove":       {'price': 108, 'zone': 'Far North'},
    "Coomera":              {'price': 108, 'zone': 'Far North'},
    "Upper Coomera":        {'price': 110, 'zone': 'Far North'},
    "Oxenford":             {'price': 108, 'zone': 'Far North'},
    "Pacific Pines":        {'price': 105, 'zone': 'Far North'},
    "Maudsland":            {'price': 110, 'zone': 'Far North'},
    "Pimpama":              {'price': 112, 'zone': 'Far North'},
    "Ormeau":               {'price': 118, 'zone': 'Far North'},
    "Ormeau Hills":         {'price': 118, 'zone': 'Far North'},
    "Yatala":               {'price': 122, 'zone': 'Far North'},
    "Jacobs Well":          {'price': 125, 'zone': 'Far North'},

    # Hinterland — inland suburbs (west), priced by road distance from OOL
    "Mudgeeraba":           {'price': 80,  'zone': 'Hinterland'},
    "Worongary":            {'price': 85,  'zone': 'Hinterland'},
    "Bonogin":              {'price': 88,  'zone': 'Hinterland'},
    "Varsity Lakes":        {'price': 88,  'zone': 'Hinterland'},
    "Robina":               {'price': 85,  'zone': 'Hinterland'},
    "Merrimac":             {'price': 88,  'zone': 'Hinterland'},
    "Clear Island Waters":  {'price': 90,  'zone': 'Hinterland'},
    "Reedy Creek":          {'price': 88,  'zone': 'Hinterland'},
    "Gaven":                {'price': 92,  'zone': 'Hinterland'},
    "Gilston":              {'price': 95,  'zone': 'Hinterland'},
    "Mount Nathan":         {'price': 108, 'zone': 'Hinterland'},
    "Canungra":             {'price': 120, 'zone': 'Hinterland'},
    "Tamborine Mountain":   {'price': 125, 'zone': 'Hinterland'},
}

# Pinned items appear at the top of the booking dropdown
PINNED = {
    "Gold Coast Airport": 0,
}

EXTRA_PINNED = [
    {"name": "Gold Coast Airport", "price": 0, "zone": "Airport Surrounds"},
]


class Command(BaseCommand):
    help = 'Import Gold Coast suburbs into RegionSuburb. Idempotent — safe to re-run.'

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        try:
            gold_coast = Region.objects.get(slug='gold-coast')
        except Region.DoesNotExist:
            self.stderr.write(self.style.ERROR("Gold Coast region not found. Create it first."))
            return

        created_count = 0
        updated_count = 0

        for name, data in GOLD_COAST_SUBURBS.items():
            slug = slugify(name)
            price = Decimal(str(data['price']))
            zone = data['zone']

            obj, was_created = RegionSuburb.objects.update_or_create(
                region=gold_coast,
                slug=slug,
                defaults={
                    'name': name,
                    'price': price,
                    'zone': zone,
                    'is_active': True,
                    'is_pinned': name in PINNED,
                    'sort_order': PINNED.get(name, 0),
                    'meta_title': f"{name} Airport Shuttle | EasyGo Gold Coast",
                    'meta_description': (
                        f"Private airport shuttle from {name} to Gold Coast Airport (OOL). "
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
                region=gold_coast,
                slug=slug,
                defaults={
                    'name': name,
                    'price': Decimal('0'),
                    'zone': item['zone'],
                    'is_active': True,
                    'is_pinned': True,
                    'sort_order': PINNED[name],
                    'meta_title': f"{name} | EasyGo Gold Coast",
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
