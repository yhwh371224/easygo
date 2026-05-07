from decimal import Decimal

from django.core.management.base import BaseCommand

# All Brisbane suburbs within 45km of Brisbane Airport (BNE, Eagle Farm QLD 4009).
# Pricing: $3/km, minimum $60, rounded to nearest $5.
# Airport coords: -27.3842°S, 153.1175°E
#
# Excluded: Redland Bay (~50km by road, over limit).
# Samford Valley (32km) confirmed within 45km.

SUBURBS = {
    # ── Inner Brisbane (all ≤18km — minimum $60) ─────────────────────────
    "Newstead":             {"price": "60.00", "zone": "Inner Brisbane"},  #  9km
    "Fortitude Valley":     {"price": "60.00", "zone": "Inner Brisbane"},  # 10km
    "Bowen Hills":          {"price": "60.00", "zone": "Inner Brisbane"},  # 10km
    "New Farm":             {"price": "60.00", "zone": "Inner Brisbane"},  # 11km
    "Teneriffe":            {"price": "60.00", "zone": "Inner Brisbane"},  # 11km
    "Herston":              {"price": "60.00", "zone": "Inner Brisbane"},  # 12km
    "Spring Hill":          {"price": "60.00", "zone": "Inner Brisbane"},  # 12km
    "Brisbane CBD":         {"price": "60.00", "zone": "Inner Brisbane"},  # 12km
    "South Brisbane":       {"price": "60.00", "zone": "Inner Brisbane"},  # 13km
    "West End":             {"price": "60.00", "zone": "Inner Brisbane"},  # 14km
    "Kelvin Grove":         {"price": "60.00", "zone": "Inner Brisbane"},  # 14km
    "Dutton Park":          {"price": "60.00", "zone": "Inner Brisbane"},  # 14km
    "Paddington":           {"price": "60.00", "zone": "Inner Brisbane"},  # 15km
    "Highgate Hill":        {"price": "60.00", "zone": "Inner Brisbane"},  # 15km
    "Red Hill":             {"price": "60.00", "zone": "Inner Brisbane"},  # 15km
    "Milton":               {"price": "60.00", "zone": "Inner Brisbane"},  # 14km
    "Auchenflower":         {"price": "60.00", "zone": "Inner Brisbane"},  # 15km
    "Bardon":               {"price": "60.00", "zone": "Inner Brisbane"},  # 18km
    "Ashgrove":             {"price": "60.00", "zone": "Inner Brisbane"},  # 18km

    # ── Inner South (~13-20 km — minimum $60) ─────────────────────────────
    "Woolloongabba":        {"price": "60.00", "zone": "Inner South"},     # 13km
    "Greenslopes":          {"price": "60.00", "zone": "Inner South"},     # 15km
    "Annerley":             {"price": "60.00", "zone": "Inner South"},     # 16km
    "Yeronga":              {"price": "60.00", "zone": "Inner South"},     # 17km
    "Moorooka":             {"price": "60.00", "zone": "Inner South"},     # 18km
    "Rocklea":              {"price": "60.00", "zone": "Inner South"},     # 19km
    "Salisbury":            {"price": "60.00", "zone": "Inner South"},     # 19km
    "Archerfield":          {"price": "60.00", "zone": "Inner South"},     # 20km
    "Acacia Ridge":         {"price": "60.00", "zone": "Inner South"},     # 19km
    "Coopers Plains":       {"price": "60.00", "zone": "Inner South"},     # 20km

    # ── Eastern (~8-20 km — minimum $60) ─────────────────────────────────
    "Murarrie":             {"price": "60.00", "zone": "Eastern"},         #  9km
    "Cannon Hill":          {"price": "60.00", "zone": "Eastern"},         #  8km
    "Morningside":          {"price": "60.00", "zone": "Eastern"},         #  9km
    "Balmoral":             {"price": "60.00", "zone": "Eastern"},         # 10km
    "Bulimba":              {"price": "60.00", "zone": "Eastern"},         # 10km
    "Hawthorne":            {"price": "60.00", "zone": "Eastern"},         # 11km
    "Tingalpa":             {"price": "60.00", "zone": "Eastern"},         # 12km
    "Belmont":              {"price": "60.00", "zone": "Eastern"},         # 14km
    "Wynnum":               {"price": "60.00", "zone": "Eastern"},         # 14km
    "Manly":                {"price": "60.00", "zone": "Eastern"},         # 17km
    "Carina":               {"price": "60.00", "zone": "Eastern"},         # 17km
    "Camp Hill":            {"price": "60.00", "zone": "Eastern"},         # 17km
    "Carina Heights":       {"price": "60.00", "zone": "Eastern"},         # 18km
    "Carindale":            {"price": "60.00", "zone": "Eastern"},         # 19km
    "Holland Park":         {"price": "60.00", "zone": "Eastern"},         # 19km
    "Holland Park West":    {"price": "60.00", "zone": "Eastern"},         # 20km
    "Lota":                 {"price": "60.00", "zone": "Eastern"},         # 19km

    # ── Eastern — southern reach (~21-24 km) ──────────────────────────────
    "Mount Gravatt":        {"price": "65.00", "zone": "Eastern"},         # 21km
    "Mount Gravatt East":   {"price": "65.00", "zone": "Eastern"},         # 21km
    "Upper Mount Gravatt":  {"price": "70.00", "zone": "Eastern"},         # 23km
    "Eight Mile Plains":    {"price": "70.00", "zone": "Eastern"},         # 24km

    # ── Northern — airport surrounds (~5-8 km — minimum $60) ─────────────
    "Hendra":               {"price": "60.00", "zone": "Northern"},        #  5km
    "Banyo":                {"price": "60.00", "zone": "Northern"},        #  6km
    "Ascot":                {"price": "60.00", "zone": "Northern"},        #  6km
    "Hamilton":             {"price": "60.00", "zone": "Northern"},        #  6km
    "Virginia":             {"price": "60.00", "zone": "Northern"},        #  7km
    "Nudgee":               {"price": "60.00", "zone": "Northern"},        #  7km
    "Nundah":               {"price": "60.00", "zone": "Northern"},        #  7km
    "Clayfield":            {"price": "60.00", "zone": "Northern"},        #  8km
    "Northgate":            {"price": "60.00", "zone": "Northern"},        #  8km
    "Albion":               {"price": "60.00", "zone": "Northern"},        #  8km

    # ── Northern — inner (~10-17 km — minimum $60) ───────────────────────
    "Geebung":              {"price": "60.00", "zone": "Northern"},        # 11km
    "Chermside":            {"price": "60.00", "zone": "Northern"},        # 11km
    "Nudgee Beach":         {"price": "60.00", "zone": "Northern"},        # 12km
    "Boondall":             {"price": "60.00", "zone": "Northern"},        # 12km
    "Taigum":               {"price": "60.00", "zone": "Northern"},        # 12km
    "Zillmere":             {"price": "60.00", "zone": "Northern"},        # 13km
    "Fitzgibbon":           {"price": "60.00", "zone": "Northern"},        # 14km
    "Aspley":               {"price": "60.00", "zone": "Northern"},        # 15km
    "Sandgate":             {"price": "60.00", "zone": "Northern"},        # 16km
    "Shorncliffe":          {"price": "60.00", "zone": "Northern"},        # 19km

    # ── Northern — outer (~21-31 km) ──────────────────────────────────────
    "Bracken Ridge":        {"price": "65.00", "zone": "Northern"},        # 21km
    "Mango Hill":           {"price": "80.00", "zone": "Northern"},        # 27km
    "Murrumba Downs":       {"price": "85.00", "zone": "Northern"},        # 28km
    "Griffin":              {"price": "85.00", "zone": "Northern"},        # 29km
    "Petrie":               {"price": "90.00", "zone": "Northern"},        # 30km
    "Kallangur":            {"price": "95.00", "zone": "Northern"},        # 31km

    # ── Southern (~20-29 km) ──────────────────────────────────────────────
    "Wishart":              {"price": "60.00", "zone": "Southern"},        # 20km
    "Nathan":               {"price": "65.00", "zone": "Southern"},        # 21km
    "Tarragindi":           {"price": "65.00", "zone": "Southern"},        # 21km
    "Mansfield":            {"price": "65.00", "zone": "Southern"},        # 21km
    "MacGregor":            {"price": "70.00", "zone": "Southern"},        # 23km
    "Robertson":            {"price": "70.00", "zone": "Southern"},        # 24km
    "Rochedale":            {"price": "70.00", "zone": "Southern"},        # 24km
    "Sunnybank":            {"price": "65.00", "zone": "Southern"},        # 22km
    "Sunnybank Hills":      {"price": "70.00", "zone": "Southern"},        # 23km
    "Runcorn":              {"price": "70.00", "zone": "Southern"},        # 23km
    "Calamvale":            {"price": "75.00", "zone": "Southern"},        # 25km
    "Stretton":             {"price": "80.00", "zone": "Southern"},        # 27km
    "Kuraby":               {"price": "80.00", "zone": "Southern"},        # 27km
    "Larapinta":            {"price": "80.00", "zone": "Southern"},        # 27km
    "Algester":             {"price": "85.00", "zone": "Southern"},        # 28km
    "Drewvale":             {"price": "85.00", "zone": "Southern"},        # 28km
    "Parkinson":            {"price": "85.00", "zone": "Southern"},        # 29km
    "Springwood":           {"price": "80.00", "zone": "Southern"},        # 27km

    # ── Western (~17-27 km) ───────────────────────────────────────────────
    "Taringa":              {"price": "60.00", "zone": "Western"},         # 17km
    "Toowong":              {"price": "60.00", "zone": "Western"},         # 16km
    "St Lucia":             {"price": "60.00", "zone": "Western"},         # 17km
    "Indooroopilly":        {"price": "60.00", "zone": "Western"},         # 18km
    "Chelmer":              {"price": "65.00", "zone": "Western"},         # 21km
    "Graceville":           {"price": "65.00", "zone": "Western"},         # 22km
    "Sherwood":             {"price": "65.00", "zone": "Western"},         # 22km
    "Fig Tree Pocket":      {"price": "65.00", "zone": "Western"},         # 21km
    "Kenmore":              {"price": "65.00", "zone": "Western"},         # 22km
    "Corinda":              {"price": "70.00", "zone": "Western"},         # 23km
    "Chapel Hill":          {"price": "65.00", "zone": "Western"},         # 22km
    "Oxley":                {"price": "70.00", "zone": "Western"},         # 24km
    "Darra":                {"price": "70.00", "zone": "Western"},         # 24km
    "Inala":                {"price": "75.00", "zone": "Western"},         # 25km
    "Richlands":            {"price": "75.00", "zone": "Western"},         # 25km
    "Wacol":                {"price": "80.00", "zone": "Western"},         # 26km
    "Brookfield":           {"price": "75.00", "zone": "Western"},         # 25km
    "Forest Lake":          {"price": "80.00", "zone": "Western"},         # 27km

    # ── North-West (~14-32 km) ────────────────────────────────────────────
    "Grange":               {"price": "60.00", "zone": "North-West"},      # 14km
    "Gordon Park":          {"price": "60.00", "zone": "North-West"},      # 14km
    "Stafford":             {"price": "60.00", "zone": "North-West"},      # 15km
    "Stafford Heights":     {"price": "60.00", "zone": "North-West"},      # 15km
    "Mitchelton":           {"price": "60.00", "zone": "North-West"},      # 17km
    "Enoggera":             {"price": "60.00", "zone": "North-West"},      # 17km
    "Gaythorne":            {"price": "60.00", "zone": "North-West"},      # 17km
    "Everton Park":         {"price": "60.00", "zone": "North-West"},      # 17km
    "McDowall":             {"price": "60.00", "zone": "North-West"},      # 18km
    "Keperra":              {"price": "60.00", "zone": "North-West"},      # 20km
    "Everton Hills":        {"price": "60.00", "zone": "North-West"},      # 20km
    "Bridgeman Downs":      {"price": "60.00", "zone": "North-West"},      # 20km
    "Albany Creek":         {"price": "65.00", "zone": "North-West"},      # 22km
    "Ferny Grove":          {"price": "70.00", "zone": "North-West"},      # 24km
    "Bunya":                {"price": "70.00", "zone": "North-West"},      # 24km
    "Eatons Hill":          {"price": "75.00", "zone": "North-West"},      # 25km
    "Warner":               {"price": "80.00", "zone": "North-West"},      # 27km
    "Strathpine":           {"price": "85.00", "zone": "North-West"},      # 28km
    "Brendale":             {"price": "85.00", "zone": "North-West"},      # 28km
    "Samford Valley":       {"price": "95.00", "zone": "North-West"},      # 32km

    # ── Redlands (~35-43 km) ─────────────────────────────────────────────
    "Cleveland":            {"price": "105.00", "zone": "Redlands"},       # 35km
    "Victoria Point":       {"price": "130.00", "zone": "Redlands"},       # 43km
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
                    f"  [{i:>3}/{total}] Created:  {name:<22} ({zone}) — ${price_int}"
                )
            else:
                skipped_count += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(f"  [{i:>3}/{total}] Exists:   {name}")

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
