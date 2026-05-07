from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

# Second batch of Melbourne suburbs.
# Prices: $3/km from Melbourne Airport (Tullamarine), $60 minimum, rounded to nearest $5.
# Suburbs already in DB (Northcote, Bayswater, Boronia, Mill Park, South Morang, Oakleigh)
# will be silently skipped by get_or_create.

MELBOURNE_SUBURBS_2 = {
    # Inner South (~21-25 km)
    "South Melbourne":      {'price': 65,  'zone': 'Inner South',       'km': 22},
    "Port Melbourne":       {'price': 65,  'zone': 'Inner South',       'km': 21},
    "Albert Park":          {'price': 70,  'zone': 'Inner South',       'km': 24},
    "Middle Park":          {'price': 75,  'zone': 'Inner South',       'km': 25},

    # Inner North (~22-23 km)
    "Northcote":            {'price': 70,  'zone': 'Inner North',       'km': 23},  # exists → skipped
    "Thornbury":            {'price': 65,  'zone': 'Inner North',       'km': 22},

    # Inner East (~28-29 km)
    "Balwyn":               {'price': 85,  'zone': 'Inner East',        'km': 28},
    "Balwyn North":         {'price': 85,  'zone': 'Inner East',        'km': 28},
    "Burwood":              {'price': 85,  'zone': 'Inner East',        'km': 29},

    # Eastern Suburbs (~31-38 km)
    "Mont Albert":          {'price': 95,  'zone': 'Eastern Suburbs',   'km': 32},
    "Blackburn":            {'price': 95,  'zone': 'Eastern Suburbs',   'km': 32},
    "Blackburn North":      {'price': 95,  'zone': 'Eastern Suburbs',   'km': 31},
    "Forest Hill":          {'price': 105, 'zone': 'Eastern Suburbs',   'km': 35},
    "Burwood East":         {'price': 95,  'zone': 'Eastern Suburbs',   'km': 31},
    "Wantirna":             {'price': 110, 'zone': 'Eastern Suburbs',   'km': 37},
    "Wantirna South":       {'price': 115, 'zone': 'Eastern Suburbs',   'km': 38},
    "Bayswater":            {'price': 115, 'zone': 'Eastern Suburbs',   'km': 38},  # exists → skipped
    "Boronia":              {'price': 120, 'zone': 'Eastern Suburbs',   'km': 40},  # exists → skipped

    # North-East (~26-36 km)
    "Rosanna":              {'price': 80,  'zone': 'North-East',        'km': 26},
    "Viewbank":             {'price': 80,  'zone': 'North-East',        'km': 26},
    "Macleod":              {'price': 80,  'zone': 'North-East',        'km': 26},
    "Watsonia":             {'price': 80,  'zone': 'North-East',        'km': 27},
    "Templestowe Lower":    {'price': 80,  'zone': 'North-East',        'km': 27},
    "Templestowe":          {'price': 85,  'zone': 'North-East',        'km': 29},
    "Lower Plenty":         {'price': 90,  'zone': 'North-East',        'km': 30},
    "Doncaster East":       {'price': 95,  'zone': 'North-East',        'km': 31},
    "Montmorency":          {'price': 95,  'zone': 'North-East',        'km': 31},
    "Warrandyte":           {'price': 110, 'zone': 'North-East',        'km': 36},

    # Northern Suburbs (~15-33 km)
    "Fawkner":              {'price': 60,  'zone': 'Northern Suburbs',  'km': 15},
    "Glenroy":              {'price': 60,  'zone': 'Northern Suburbs',  'km': 16},
    "Oak Park":             {'price': 60,  'zone': 'Northern Suburbs',  'km': 17},
    "Pascoe Vale":          {'price': 60,  'zone': 'Northern Suburbs',  'km': 18},
    "Kingsbury":            {'price': 70,  'zone': 'Northern Suburbs',  'km': 23},
    "Thomastown":           {'price': 65,  'zone': 'Northern Suburbs',  'km': 22},
    "Lalor":                {'price': 65,  'zone': 'Northern Suburbs',  'km': 21},
    "Mill Park":            {'price': 85,  'zone': 'Northern Suburbs',  'km': 25},  # exists → skipped
    "South Morang":         {'price': 85,  'zone': 'Northern Suburbs',  'km': 27},  # exists → skipped
    "Mernda":               {'price': 95,  'zone': 'Northern Suburbs',  'km': 31},
    "Doreen":               {'price': 100, 'zone': 'Northern Suburbs',  'km': 33},

    # Inner North/West (~5-15 km — minimum applies)
    "Tullamarine":          {'price': 60,  'zone': 'Inner North/West',  'km': 5},
    "Airport West":         {'price': 60,  'zone': 'Inner North/West',  'km': 8},
    "Niddrie":              {'price': 60,  'zone': 'Inner North/West',  'km': 12},
    "Strathmore":           {'price': 60,  'zone': 'Inner North/West',  'km': 13},
    "Essendon North":       {'price': 60,  'zone': 'Inner North/West',  'km': 13},
    "Aberfeldie":           {'price': 60,  'zone': 'Inner North/West',  'km': 14},

    # Western Suburbs (~14-30 km)
    "Avondale Heights":     {'price': 60,  'zone': 'Western Suburbs',   'km': 14},
    "Sunshine North":       {'price': 60,  'zone': 'Western Suburbs',   'km': 15},
    "Kings Park":           {'price': 60,  'zone': 'Western Suburbs',   'km': 17},
    "St Albans":            {'price': 60,  'zone': 'Western Suburbs',   'km': 16},
    "Albanvale":            {'price': 60,  'zone': 'Western Suburbs',   'km': 19},
    "Sunshine West":        {'price': 60,  'zone': 'Western Suburbs',   'km': 18},
    "Maribyrnong":          {'price': 60,  'zone': 'Western Suburbs',   'km': 18},
    "Derrimut":             {'price': 65,  'zone': 'Western Suburbs',   'km': 22},
    "Truganina":            {'price': 85,  'zone': 'Western Suburbs',   'km': 28},
    "Tarneit":              {'price': 90,  'zone': 'Western Suburbs',   'km': 30},

    # South-East (~34-45 km)
    "Heatherton":           {'price': 100, 'zone': 'South-East',        'km': 34},
    "Dingley Village":      {'price': 110, 'zone': 'South-East',        'km': 37},
    "Oakleigh":             {'price': 110, 'zone': 'South-East',        'km': 37},  # exists → skipped
    "Oakleigh East":        {'price': 110, 'zone': 'South-East',        'km': 37},
    "Oakleigh South":       {'price': 115, 'zone': 'South-East',        'km': 38},
    "Huntingdale":          {'price': 115, 'zone': 'South-East',        'km': 38},
    "Mentone":              {'price': 110, 'zone': 'South-East',        'km': 36},
    "Mordialloc":           {'price': 115, 'zone': 'South-East',        'km': 38},
    "Mulgrave":             {'price': 120, 'zone': 'South-East',        'km': 40},
    "Wheelers Hill":        {'price': 125, 'zone': 'South-East',        'km': 42},
    "Rowville":             {'price': 130, 'zone': 'South-East',        'km': 43},
    "Springvale South":     {'price': 130, 'zone': 'South-East',        'km': 43},
    "Keysborough":          {'price': 130, 'zone': 'South-East',        'km': 44},
    "Lysterfield":          {'price': 130, 'zone': 'South-East',        'km': 44},
    "Bangholme":            {'price': 135, 'zone': 'South-East',        'km': 45},
}


class Command(BaseCommand):
    help = 'Add second batch of Melbourne suburbs to RegionSuburb. Idempotent — safe to re-run.'

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        try:
            melbourne = Region.objects.get(slug='melbourne')
        except Region.DoesNotExist:
            self.stderr.write(self.style.ERROR("Melbourne region not found."))
            return

        created_count = 0
        skipped_count = 0

        for name, data in MELBOURNE_SUBURBS_2.items():
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
            f"Done. Created: {created_count}, Skipped (already exist): {skipped_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total active Melbourne suburbs: {total}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Price range: ${min_price} – ${max_price}"
        ))
