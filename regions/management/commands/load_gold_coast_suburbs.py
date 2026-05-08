from decimal import Decimal

from django.core.management.base import BaseCommand

# All Gold Coast suburbs within ~68km of Gold Coast Airport (OOL, Bilinga QLD 4225).
# Pricing: distance_km × $3, minimum $60, rounded to nearest $5.
# Airport coords: -28.1644°S, 153.5050°E
#
# OOL is at the far south of the city — distances increase heading north.

SUBURBS = {
    # ── Southern Beaches (0–10 km — all minimum $60) ─────────────────────
    "Bilinga":               {"price": "60.00", "zone": "Southern Beaches"},  #  2km
    "Coolangatta":           {"price": "60.00", "zone": "Southern Beaches"},  #  3km
    "Tugun":                 {"price": "60.00", "zone": "Southern Beaches"},  #  4km
    "Currumbin":             {"price": "60.00", "zone": "Southern Beaches"},  #  6km
    "Palm Beach":            {"price": "60.00", "zone": "Southern Beaches"},  #  8km
    "Elanora":               {"price": "60.00", "zone": "Southern Beaches"},  #  8km

    # ── Southern Gold Coast (10–18 km — all minimum $60) ─────────────────
    "Tallebudgera":          {"price": "60.00", "zone": "Southern Gold Coast"},  # 12km
    "Currumbin Valley":      {"price": "60.00", "zone": "Southern Gold Coast"},  # 13km
    "Burleigh Heads":        {"price": "60.00", "zone": "Southern Gold Coast"},  # 13km
    "Burleigh Waters":       {"price": "60.00", "zone": "Southern Gold Coast"},  # 13km
    "Currumbin Waters":      {"price": "60.00", "zone": "Southern Gold Coast"},  # 13km
    "Miami":                 {"price": "60.00", "zone": "Southern Gold Coast"},  # 14km
    "Reedy Creek":           {"price": "60.00", "zone": "Southern Gold Coast"},  # 17km
    "Mermaid Beach":         {"price": "60.00", "zone": "Southern Gold Coast"},  # 17km
    "Mermaid Waters":        {"price": "60.00", "zone": "Southern Gold Coast"},  # 18km
    "Varsity Lakes":         {"price": "60.00", "zone": "Southern Gold Coast"},  # 18km

    # ── Central Gold Coast (18–26 km) ─────────────────────────────────────
    "Broadbeach":            {"price": "60.00", "zone": "Central Gold Coast"},  # 20km
    "Broadbeach Waters":     {"price": "60.00", "zone": "Central Gold Coast"},  # 20km
    "Mudgeeraba":            {"price": "60.00", "zone": "Central Gold Coast"},  # 21km
    "Merrimac":              {"price": "65.00", "zone": "Central Gold Coast"},  # 21km
    "Surfers Paradise":      {"price": "65.00", "zone": "Central Gold Coast"},  # 22km
    "Robina":                {"price": "65.00", "zone": "Central Gold Coast"},  # 22km
    "Clear Island Waters":   {"price": "65.00", "zone": "Central Gold Coast"},  # 22km
    "Bonogin":               {"price": "65.00", "zone": "Central Gold Coast"},  # 22km
    "Bundall":               {"price": "70.00", "zone": "Central Gold Coast"},  # 23km
    "Tallai":                {"price": "70.00", "zone": "Central Gold Coast"},  # 24km
    "Main Beach":            {"price": "75.00", "zone": "Central Gold Coast"},  # 25km
    "Benowa":                {"price": "75.00", "zone": "Central Gold Coast"},  # 26km
    "Tallebudgera Valley":   {"price": "75.00", "zone": "Central Gold Coast"},  # 26km

    # ── Northern Gold Coast (26–35 km) ────────────────────────────────────
    "Worongary":             {"price": "80.00", "zone": "Northern Gold Coast"},  # 27km
    "Highland Park":         {"price": "80.00", "zone": "Northern Gold Coast"},  # 27km
    "Ashmore":               {"price": "85.00", "zone": "Northern Gold Coast"},  # 28km
    "Neranwood":             {"price": "85.00", "zone": "Northern Gold Coast"},  # 28km
    "Southport":             {"price": "85.00", "zone": "Northern Gold Coast"},  # 28km
    "Carrara":               {"price": "85.00", "zone": "Northern Gold Coast"},  # 29km
    "Molendinar":            {"price": "90.00", "zone": "Northern Gold Coast"},  # 29km
    "Labrador":              {"price": "90.00", "zone": "Northern Gold Coast"},  # 30km
    "Nerang":                {"price": "90.00", "zone": "Northern Gold Coast"},  # 30km
    "Biggera Waters":        {"price": "95.00", "zone": "Northern Gold Coast"},  # 31km
    "Gilston":               {"price": "95.00", "zone": "Northern Gold Coast"},  # 32km
    "Austinville":           {"price": "95.00", "zone": "Northern Gold Coast"},  # 32km
    "Runaway Bay":           {"price": "95.00", "zone": "Northern Gold Coast"},  # 32km
    "Parkwood":              {"price": "100.00", "zone": "Northern Gold Coast"}, # 33km
    "Arundel":               {"price": "100.00", "zone": "Northern Gold Coast"}, # 33km
    "Hollywell":             {"price": "105.00", "zone": "Northern Gold Coast"}, # 34km

    # ── Outer Northern Gold Coast (35–53 km) ──────────────────────────────
    "Paradise Point":        {"price": "105.00", "zone": "Outer Northern Gold Coast"}, # 35km
    "Gaven":                 {"price": "105.00", "zone": "Outer Northern Gold Coast"}, # 35km
    "Coombabah":             {"price": "110.00", "zone": "Outer Northern Gold Coast"}, # 36km
    "Advancetown":           {"price": "115.00", "zone": "Outer Northern Gold Coast"}, # 38km
    "Pacific Pines":         {"price": "115.00", "zone": "Outer Northern Gold Coast"}, # 39km
    "Mount Nathan":          {"price": "120.00", "zone": "Outer Northern Gold Coast"}, # 39km
    "Clagiraba":             {"price": "120.00", "zone": "Outer Northern Gold Coast"}, # 39km
    "Helensvale":            {"price": "120.00", "zone": "Outer Northern Gold Coast"}, # 40km
    "Lower Beechmont":       {"price": "120.00", "zone": "Outer Northern Gold Coast"}, # 41km
    "Maudsland":             {"price": "125.00", "zone": "Outer Northern Gold Coast"}, # 41km
    "Springbrook":           {"price": "130.00", "zone": "Outer Northern Gold Coast"}, # 43km
    "Oxenford":              {"price": "130.00", "zone": "Outer Northern Gold Coast"}, # 43km
    "Guanaba":               {"price": "135.00", "zone": "Outer Northern Gold Coast"}, # 45km
    "Alberton":              {"price": "140.00", "zone": "Outer Northern Gold Coast"}, # 47km
    "Hope Island":           {"price": "145.00", "zone": "Outer Northern Gold Coast"}, # 48km
    "Upper Coomera":         {"price": "145.00", "zone": "Outer Northern Gold Coast"}, # 48km
    "Numinbah Valley":       {"price": "150.00", "zone": "Outer Northern Gold Coast"}, # 49km
    "Coomera":               {"price": "150.00", "zone": "Outer Northern Gold Coast"}, # 50km
    "Willow Vale":           {"price": "150.00", "zone": "Outer Northern Gold Coast"}, # 51km
    "Pimpama":               {"price": "155.00", "zone": "Outer Northern Gold Coast"}, # 52km
    "Wongawallan":           {"price": "155.00", "zone": "Outer Northern Gold Coast"}, # 52km

    # ── Far Northern Fringe (53–68 km) ────────────────────────────────────
    "Norwell":               {"price": "170.00", "zone": "Far Northern Fringe"},  # 56km
    "Jacobs Well":           {"price": "175.00", "zone": "Far Northern Fringe"},  # 59km
    "Ormeau":                {"price": "180.00", "zone": "Far Northern Fringe"},  # 59km
    "Kingsholme":            {"price": "180.00", "zone": "Far Northern Fringe"},  # 60km
    "Ormeau Hills":          {"price": "180.00", "zone": "Far Northern Fringe"},  # 61km
    "Woongoolba":            {"price": "185.00", "zone": "Far Northern Fringe"},  # 62km
    "Yatala":                {"price": "185.00", "zone": "Far Northern Fringe"},  # 62km
    "Stapylton":             {"price": "190.00", "zone": "Far Northern Fringe"},  # 63km
    "Steiglitz":             {"price": "190.00", "zone": "Far Northern Fringe"},  # 63km
    "Luscombe":              {"price": "190.00", "zone": "Far Northern Fringe"},  # 64km
    "Gilberton":             {"price": "190.00", "zone": "Far Northern Fringe"},  # 64km
    "Natural Bridge":        {"price": "185.00", "zone": "Far Northern Fringe"},  # 61km
    "Cedar Creek":           {"price": "205.00", "zone": "Far Northern Fringe"},  # 68km
}


class Command(BaseCommand):
    help = (
        "Load all Gold Coast suburbs into RegionSuburb. "
        "Idempotent — safe to re-run on production. "
        "Uses get_or_create by (region, name); never duplicates."
    )

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        # ── 1. Get or create the Gold Coast region ────────────────────────
        gold_coast, region_created = Region.objects.get_or_create(
            slug="gold-coast",
            defaults={
                "name": "Gold Coast",
                "state_code": "QLD",
                "timezone": "Australia/Brisbane",
                "is_active": True,
            },
        )
        if region_created:
            self.stdout.write(self.style.WARNING("Created Gold Coast region (was missing)."))
        else:
            self.stdout.write(f"Gold Coast region found (pk={gold_coast.pk}).")

        # ── 2. Load suburbs ───────────────────────────────────────────────
        created_count = 0
        skipped_count = 0
        total = len(SUBURBS)

        for i, (name, data) in enumerate(SUBURBS.items(), start=1):
            price = Decimal(data["price"])
            zone = data["zone"]
            price_int = int(price)

            obj, was_created = RegionSuburb.objects.get_or_create(
                region=gold_coast,
                name=name,
                defaults={
                    "slug": name.lower().replace(" ", "-").replace("'", ""),
                    "price": price,
                    "zone": zone,
                    "is_active": True,
                    "meta_title": f"{name} Airport Shuttle | EasyGo Gold Coast",
                    "meta_description": (
                        f"Private airport shuttle from {name} to Gold Coast Airport (OOL). "
                        f"Fixed price from ${price_int} per vehicle. "
                        "Door-to-door, meet & greet, flight tracking included. Book online."
                    ),
                },
            )

            if was_created:
                created_count += 1
                self.stdout.write(
                    f"  [{i:>3}/{total}] Created:  {name:<26} ({zone}) — ${price_int}"
                )
            else:
                skipped_count += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(f"  [{i:>3}/{total}] Exists:   {name}")

        # ── 3. Summary ────────────────────────────────────────────────────
        qs = RegionSuburb.objects.filter(region=gold_coast, is_active=True, is_pinned=False)
        total_db = qs.count()
        prices = list(qs.values_list("price", flat=True))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created_count}  |  Already existed: {skipped_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total active Gold Coast suburbs in DB: {total_db}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Price range: ${min(prices)} – ${max(prices)}"
        ))
