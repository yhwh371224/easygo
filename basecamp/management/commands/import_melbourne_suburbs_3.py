from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

# Third batch of Melbourne suburbs — gap-fill pass.
# Prices: $3/km from Melbourne Airport (Tullamarine), $60 minimum, rounded to nearest $5.
# Suburbs already in DB are listed with a comment and will be silently skipped (get_or_create).

MELBOURNE_SUBURBS_3 = {
    # ── Bayside (~33-39 km) ───────────────────────────────────────────────
    # Brighton already exists ($88)
    "Brighton East":    {'price': 100, 'zone': 'Inner South',       'km': 33},
    "Hampton":          {'price': 100, 'zone': 'Inner South',       'km': 34},
    "Sandringham":      {'price': 110, 'zone': 'South-East',        'km': 36},
    "Black Rock":       {'price': 115, 'zone': 'South-East',        'km': 38},
    "Beaumaris":        {'price': 115, 'zone': 'South-East',        'km': 39},
    # Mentone already exists ($110)
    "Parkdale":         {'price': 110, 'zone': 'South-East',        'km': 37},

    # ── Inner South — Armadale corridor (~26-27 km) ───────────────────────
    # Prahran, Windsor already exist
    "Hawksburn":        {'price': 80,  'zone': 'Inner South',       'km': 26},
    "Armadale":         {'price': 80,  'zone': 'Inner South',       'km': 27},

    # ── Inner East — Malvern / Caulfield / Glen Iris (~27-32 km) ─────────
    # Toorak, Hawthorn, Camberwell already exist
    "Kooyong":          {'price': 85,  'zone': 'Inner East',        'km': 28},
    "Malvern":          {'price': 80,  'zone': 'Inner East',        'km': 27},
    "Glen Iris":        {'price': 85,  'zone': 'Inner East',        'km': 29},
    "Malvern East":     {'price': 90,  'zone': 'Inner East',        'km': 30},
    "Caulfield North":  {'price': 85,  'zone': 'Inner East',        'km': 29},
    "Caulfield":        {'price': 90,  'zone': 'Inner East',        'km': 30},
    "Caulfield South":  {'price': 95,  'zone': 'Inner East',        'km': 32},

    # ── Eastern — SE corridor (~32-33 km) ────────────────────────────────
    # Glen Waverley already exists ($90)
    "Mount Waverley":   {'price': 95,  'zone': 'Eastern Suburbs',   'km': 32},
    "Notting Hill":     {'price': 100, 'zone': 'Eastern Suburbs',   'km': 33},

    # ── Northern — close to airport (~8-19 km, all minimum) ──────────────
    # Reservoir, Coburg already exist
    "Coburg North":     {'price': 60,  'zone': 'Northern Suburbs',  'km': 19},
    "Batman":           {'price': 60,  'zone': 'Inner North',       'km': 20},
    "Westmeadows":      {'price': 60,  'zone': 'Inner North/West',  'km': 8},
    "Gladstone Park":   {'price': 60,  'zone': 'Inner North/West',  'km': 12},
    "Greenvale":        {'price': 60,  'zone': 'Northern Suburbs',  'km': 14},

    # ── Western (~38 km) ─────────────────────────────────────────────────
    # Point Cook, Hoppers Crossing already exist
    "Wyndham Vale":     {'price': 115, 'zone': 'Western Suburbs',   'km': 38},

    # ── Eastern — Croydon / Ringwood fringe (~40-42 km) ──────────────────
    # Croydon already exists ($95)
    "Croydon North":    {'price': 120, 'zone': 'Eastern Suburbs',   'km': 40},
    "Croydon South":    {'price': 120, 'zone': 'Eastern Suburbs',   'km': 40},
    "Ringwood East":    {'price': 125, 'zone': 'Eastern Suburbs',   'km': 42},
    "Heathmont":        {'price': 120, 'zone': 'Eastern Suburbs',   'km': 40},
}


class Command(BaseCommand):
    help = 'Add third batch of Melbourne suburbs (gap-fill). Idempotent — safe to re-run.'

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        try:
            melbourne = Region.objects.get(slug='melbourne')
        except Region.DoesNotExist:
            self.stderr.write(self.style.ERROR("Melbourne region not found."))
            return

        created_count = 0
        skipped_count = 0

        for name, data in MELBOURNE_SUBURBS_3.items():
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
                self.stdout.write(f"  Created: {name:<22} ({zone}) — ${int(price)}  [{km}km]")
            else:
                skipped_count += 1
                self.stdout.write(f"  Skipped (exists): {name}")

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
