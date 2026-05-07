from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

# New Melbourne suburbs not yet in the database.
# Prices: $3/km from Melbourne Airport (Tullamarine), $60 minimum, rounded to nearest $5.
NEW_MELBOURNE_SUBURBS = {
    # Central Melbourne (~20-25 km)
    "Docklands":        {'price': 60,  'zone': 'Central Melbourne', 'km': 20},
    "Collingwood":      {'price': 75,  'zone': 'Central Melbourne', 'km': 25},

    # Eastern Suburbs (~34-38 km)
    "Nunawading":       {'price': 100, 'zone': 'Eastern Suburbs',   'km': 34},
    "Mitcham":          {'price': 110, 'zone': 'Eastern Suburbs',   'km': 37},
    "Vermont":          {'price': 115, 'zone': 'Eastern Suburbs',   'km': 38},

    # Northern Suburbs (~12 km — minimum applies)
    "Broadmeadows":     {'price': 60,  'zone': 'Northern Suburbs',  'km': 12},

    # Western Suburbs (~17-22 km)
    "Sunshine":         {'price': 60,  'zone': 'Western Suburbs',   'km': 17},
    "Deer Park":        {'price': 65,  'zone': 'Western Suburbs',   'km': 22},

    # Inner North/West (~9 km — minimum applies)
    "Keilor":           {'price': 60,  'zone': 'Inner North/West',  'km': 9},

    # South-East (~31-43 km)
    "Cheltenham":       {'price': 95,  'zone': 'South-East',        'km': 31},
    "Moorabbin":        {'price': 95,  'zone': 'South-East',        'km': 32},
    "Clayton":          {'price': 110, 'zone': 'South-East',        'km': 36},
    "Noble Park":       {'price': 130, 'zone': 'South-East',        'km': 43},
}


class Command(BaseCommand):
    help = 'Add missing Melbourne suburbs to RegionSuburb. Idempotent — safe to re-run.'

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        try:
            melbourne = Region.objects.get(slug='melbourne')
        except Region.DoesNotExist:
            self.stderr.write(self.style.ERROR("Melbourne region not found."))
            return

        created_count = 0
        skipped_count = 0

        for name, data in NEW_MELBOURNE_SUBURBS.items():
            slug = slugify(name)
            price = Decimal(str(data['price']))
            zone = data['zone']
            km = data['km']

            obj, was_created = RegionSuburb.objects.get_or_create(
                region=melbourne,
                slug=slug,
                defaults={
                    'name': name,
                    'price': price,
                    'zone': zone,
                    'is_active': True,
                    'meta_title': f"{name} Airport Shuttle | EasyGo Melbourne",
                    'meta_description': (
                        f"Private airport shuttle from {name} to Melbourne Airport (MEL). "
                        f"~{km} km from Tullamarine. Fixed price from ${int(price)} per vehicle. "
                        "Door-to-door, meet & greet, flight tracking included. Book online."
                    ),
                },
            )
            if was_created:
                created_count += 1
                self.stdout.write(f"  Created: {name} ({zone}) — ${int(price)}")
            else:
                skipped_count += 1
                self.stdout.write(f"  Skipped (exists): {name}")

        # Report total count and price range across all active non-pinned Melbourne suburbs
        qs = RegionSuburb.objects.filter(region=melbourne, is_active=True, is_pinned=False)
        total = qs.count()
        prices = list(qs.values_list('price', flat=True))
        min_price = min(prices)
        max_price = max(prices)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created_count}, Skipped: {skipped_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total active Melbourne suburbs: {total}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Price range: ${min_price} – ${max_price}"
        ))
