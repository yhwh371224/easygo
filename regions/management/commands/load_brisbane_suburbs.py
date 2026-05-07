from decimal import Decimal

from django.core.management.base import BaseCommand

# All Brisbane suburbs within 45km of Brisbane Airport (BNE, Eagle Farm QLD 4009).
# Pricing: $3/km, minimum $60, rounded to nearest $5.
# Airport coords: -27.3842°S, 153.1175°E
#
# Redland Bay (~50km by road) excluded — over 45km limit.
# Cleveland (35km) and Victoria Point (43km) confirmed within limit.

SUBURBS = {
    # ── Inner Brisbane (all ≤15km — minimum $60) ─────────────────────────
    "Hendra":               {"price": "60.00", "zone": "Northern"},
    "Ascot":                {"price": "60.00", "zone": "Northern"},
    "Hamilton":             {"price": "60.00", "zone": "Northern"},
    "Nundah":               {"price": "60.00", "zone": "Northern"},
    "Clayfield":            {"price": "60.00", "zone": "Northern"},
    "Albion":               {"price": "60.00", "zone": "Northern"},
    "Bowen Hills":          {"price": "60.00", "zone": "Inner Brisbane"},
    "Newstead":             {"price": "60.00", "zone": "Inner Brisbane"},
    "Fortitude Valley":     {"price": "60.00", "zone": "Inner Brisbane"},
    "New Farm":             {"price": "60.00", "zone": "Inner Brisbane"},
    "Teneriffe":            {"price": "60.00", "zone": "Inner Brisbane"},
    "Spring Hill":          {"price": "60.00", "zone": "Inner Brisbane"},
    "Brisbane CBD":         {"price": "60.00", "zone": "Inner Brisbane"},
    "South Brisbane":       {"price": "60.00", "zone": "Inner Brisbane"},
    "West End":             {"price": "60.00", "zone": "Inner Brisbane"},
    "Paddington":           {"price": "60.00", "zone": "Inner Brisbane"},
    "Milton":               {"price": "60.00", "zone": "Inner Brisbane"},
    "Auchenflower":         {"price": "60.00", "zone": "Inner Brisbane"},
    "Toowong":              {"price": "60.00", "zone": "Western"},
    "St Lucia":             {"price": "60.00", "zone": "Western"},
    "Indooroopilly":        {"price": "60.00", "zone": "Western"},

    # ── Inner South (~13-20 km — minimum $60) ─────────────────────────────
    "Woolloongabba":        {"price": "60.00", "zone": "Inner South"},
    "Greenslopes":          {"price": "60.00", "zone": "Inner South"},
    "Annerley":             {"price": "60.00", "zone": "Inner South"},
    "Yeronga":              {"price": "60.00", "zone": "Inner South"},
    "Moorooka":             {"price": "60.00", "zone": "Inner South"},
    "Rocklea":              {"price": "60.00", "zone": "Inner South"},
    "Salisbury":            {"price": "60.00", "zone": "Inner South"},
    "Archerfield":          {"price": "60.00", "zone": "Inner South"},
    "Acacia Ridge":         {"price": "60.00", "zone": "Inner South"},
    "Coopers Plains":       {"price": "60.00", "zone": "Inner South"},

    # ── Eastern (~8-19 km — minimum $60) ─────────────────────────────────
    "Cannon Hill":          {"price": "60.00", "zone": "Eastern"},
    "Morningside":          {"price": "60.00", "zone": "Eastern"},
    "Balmoral":             {"price": "60.00", "zone": "Eastern"},
    "Bulimba":              {"price": "60.00", "zone": "Eastern"},
    "Hawthorne":            {"price": "60.00", "zone": "Eastern"},
    "Tingalpa":             {"price": "60.00", "zone": "Eastern"},
    "Wynnum":               {"price": "60.00", "zone": "Eastern"},
    "Manly":                {"price": "60.00", "zone": "Eastern"},
    "Lota":                 {"price": "60.00", "zone": "Eastern"},

    # ── Northern (~11-17 km — minimum $60) ───────────────────────────────
    "Chermside":            {"price": "60.00", "zone": "Northern"},
    "Aspley":               {"price": "60.00", "zone": "Northern"},
    "Sandgate":             {"price": "60.00", "zone": "Northern"},
    "Shorncliffe":          {"price": "60.00", "zone": "Northern"},
    "Mitchelton":           {"price": "60.00", "zone": "North-West"},
    "Enoggera":             {"price": "60.00", "zone": "North-West"},
    "Gaythorne":            {"price": "60.00", "zone": "North-West"},
    "Everton Park":         {"price": "60.00", "zone": "North-West"},
    "Keperra":              {"price": "60.00", "zone": "North-West"},

    # ── Southern (~20-21 km) ──────────────────────────────────────────────
    "Wishart":              {"price": "60.00", "zone": "Southern"},
    "Mansfield":            {"price": "65.00", "zone": "Southern"},   # 21km

    # ── Northern reach (~21-22 km) ────────────────────────────────────────
    "Bracken Ridge":        {"price": "65.00", "zone": "Northern"},   # 21km

    # ── Southern (~22-27 km) ──────────────────────────────────────────────
    "Sunnybank":            {"price": "65.00", "zone": "Southern"},   # 22km
    "Sunnybank Hills":      {"price": "70.00", "zone": "Southern"},   # 23km
    "Runcorn":              {"price": "70.00", "zone": "Southern"},   # 23km
    "Rochedale":            {"price": "70.00", "zone": "Southern"},   # 24km
    "Calamvale":            {"price": "75.00", "zone": "Southern"},   # 25km
    "Springwood":           {"price": "80.00", "zone": "Southern"},   # 27km

    # ── Western (~21-25 km) ───────────────────────────────────────────────
    "Fig Tree Pocket":      {"price": "65.00", "zone": "Western"},    # 21km
    "Kenmore":              {"price": "65.00", "zone": "Western"},    # 22km
    "Chapel Hill":          {"price": "65.00", "zone": "Western"},    # 22km
    "Brookfield":           {"price": "75.00", "zone": "Western"},    # 25km

    # ── North-West (~22-28 km) ────────────────────────────────────────────
    "Albany Creek":         {"price": "65.00", "zone": "North-West"}, # 22km
    "Ferny Grove":          {"price": "70.00", "zone": "North-West"}, # 24km
    "Eatons Hill":          {"price": "75.00", "zone": "North-West"}, # 25km
    "Warner":               {"price": "80.00", "zone": "North-West"}, # 27km
    "Strathpine":           {"price": "85.00", "zone": "North-West"}, # 28km
    "Brendale":             {"price": "85.00", "zone": "North-West"}, # 28km

    # ── North — Moreton Bay (~26-31 km) ──────────────────────────────────
    "Mango Hill":           {"price": "80.00", "zone": "Northern"},   # 27km
    "Murrumba Downs":       {"price": "85.00", "zone": "Northern"},   # 28km
    "Griffin":              {"price": "85.00", "zone": "Northern"},   # 29km
    "Kallangur":            {"price": "95.00", "zone": "Northern"},   # 31km
    "Petrie":               {"price": "90.00", "zone": "Northern"},   # 30km

    # ── Redlands (~35-43 km) ─────────────────────────────────────────────
    "Cleveland":            {"price": "105.00", "zone": "Redlands"},  # 35km
    "Victoria Point":       {"price": "130.00", "zone": "Redlands"},  # 43km
}


class Command(BaseCommand):
    help = (
        "Load all Brisbane suburbs into RegionSuburb. "
        "Idempotent — safe to re-run on production. "
        "Uses get_or_create by (region, name); never duplicates."
    )

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        # ── 1. Get or create the Brisbane region ──────────────────────────
        brisbane, region_created = Region.objects.get_or_create(
            slug="brisbane",
            defaults={
                "name": "Brisbane",
                "state_code": "QLD",
                "timezone": "Australia/Brisbane",
                "is_active": True,
            },
        )
        if region_created:
            self.stdout.write(self.style.WARNING("Created Brisbane region (was missing)."))
        else:
            self.stdout.write(f"Brisbane region found (pk={brisbane.pk}).")

        # ── 2. Load suburbs ───────────────────────────────────────────────
        created_count = 0
        skipped_count = 0
        total = len(SUBURBS)

        for i, (name, data) in enumerate(SUBURBS.items(), start=1):
            price = Decimal(data["price"])
            zone = data["zone"]
            price_int = int(price)

            obj, was_created = RegionSuburb.objects.get_or_create(
                region=brisbane,
                name=name,
                defaults={
                    "slug": name.lower().replace(" ", "-").replace("'", ""),
                    "price": price,
                    "zone": zone,
                    "is_active": True,
                    "meta_title": f"{name} Airport Shuttle | EasyGo Brisbane",
                    "meta_description": (
                        f"Private airport shuttle from {name} to Brisbane Airport (BNE). "
                        f"Fixed price from ${price_int} per vehicle. "
                        "Door-to-door, meet & greet, flight tracking included. Book online."
                    ),
                },
            )

            if was_created:
                created_count += 1
                self.stdout.write(
                    f"  [{i:>2}/{total}] Created:  {name:<22} ({zone}) — ${price_int}"
                )
            else:
                skipped_count += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(f"  [{i:>2}/{total}] Exists:   {name}")

        # ── 3. Summary ────────────────────────────────────────────────────
        qs = RegionSuburb.objects.filter(region=brisbane, is_active=True, is_pinned=False)
        total_db = qs.count()
        prices = list(qs.values_list("price", flat=True))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created_count}  |  Already existed: {skipped_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total active Brisbane suburbs in DB: {total_db}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Price range: ${min(prices)} – ${max(prices)}"
        ))
