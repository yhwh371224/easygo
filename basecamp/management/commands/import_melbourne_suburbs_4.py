from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

# Fourth batch — gap-fill from Glen Eira, Whitehorse, Manningham,
# Nillumbik, Hume, Melton and Wyndham LGAs.
# Prices: $3/km from Melbourne Airport (Tullamarine), $60 minimum, nearest $5.
# Note: St Andrews (Nillumbik) excluded — ~48 km by road, exceeds 45 km limit.

MELBOURNE_SUBURBS_4 = {
    # ── Glen Eira (~30-33 km) ─────────────────────────────────────────────
    "Murrumbeena":      {'price': 90,  'zone': 'South-East',        'km': 30},
    "McKinnon":         {'price': 95,  'zone': 'South-East',        'km': 31},
    "Ormond":           {'price': 95,  'zone': 'South-East',        'km': 31},
    "Carnegie":         {'price': 95,  'zone': 'South-East',        'km': 31},
    "Bentleigh":        {'price': 100, 'zone': 'South-East',        'km': 33},
    "Bentleigh East":   {'price': 100, 'zone': 'South-East',        'km': 33},

    # ── Whitehorse (~33 km) ───────────────────────────────────────────────
    "Blackburn South":  {'price': 100, 'zone': 'Eastern Suburbs',   'km': 33},

    # ── Manningham (~35-37 km) ────────────────────────────────────────────
    "Park Orchards":    {'price': 105, 'zone': 'North-East',        'km': 35},
    "Warrandyte South": {'price': 110, 'zone': 'North-East',        'km': 37},

    # ── Nillumbik (~30-32 km) ─────────────────────────────────────────────
    "Plenty":           {'price': 90,  'zone': 'North-East',        'km': 30},
    "Yarrambat":        {'price': 95,  'zone': 'North-East',        'km': 32},

    # ── Hume (~12-16 km — all minimum) ───────────────────────────────────
    "Campbellfield":    {'price': 60,  'zone': 'Northern Suburbs',  'km': 12},
    "Dallas":           {'price': 60,  'zone': 'Northern Suburbs',  'km': 13},
    "Meadow Heights":   {'price': 60,  'zone': 'Northern Suburbs',  'km': 16},

    # ── Melton City (~17-33 km) ───────────────────────────────────────────
    "Taylors Hill":     {'price': 60,  'zone': 'Western Suburbs',   'km': 17},
    "Taylors Lakes":    {'price': 60,  'zone': 'Western Suburbs',   'km': 18},
    "Hillside":         {'price': 60,  'zone': 'Western Suburbs',   'km': 18},
    "Caroline Springs": {'price': 75,  'zone': 'Western Suburbs',   'km': 25},
    "Melton South":     {'price': 100, 'zone': 'Western Suburbs',   'km': 33},

    # ── Wyndham (~28-43 km) ───────────────────────────────────────────────
    "Williams Landing": {'price': 85,  'zone': 'Western Suburbs',   'km': 28},
    "Manor Lakes":      {'price': 130, 'zone': 'Western Suburbs',   'km': 43},
}


class Command(BaseCommand):
    help = 'Add fourth batch of Melbourne suburbs (LGA gap-fill). Idempotent — safe to re-run.'

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        try:
            melbourne = Region.objects.get(slug='melbourne')
        except Region.DoesNotExist:
            self.stderr.write(self.style.ERROR("Melbourne region not found."))
            return

        created_count = 0
        skipped_count = 0

        for name, data in MELBOURNE_SUBURBS_4.items():
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

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created_count}, Skipped: {skipped_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total active Melbourne suburbs: {total}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Price range: ${min(prices)} – ${max(prices)}"
        ))
