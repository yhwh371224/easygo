from decimal import Decimal

from django.core.management.base import BaseCommand

# All 179 active Melbourne suburbs — source of truth for production seeding.
# Keyed by suburb name; (region, name) is the idempotency key.
SUBURBS = {
    # ── Inner North/West (airport surrounds, all ≤$65) ───────────────────
    "Aberfeldie":           {"price": "60.00", "zone": "Inner North/West"},
    "Airport West":         {"price": "60.00", "zone": "Inner North/West"},
    "Essendon":             {"price": "62.00", "zone": "Inner North/West"},
    "Essendon North":       {"price": "60.00", "zone": "Inner North/West"},
    "Gladstone Park":       {"price": "60.00", "zone": "Inner North/West"},
    "Keilor":               {"price": "60.00", "zone": "Inner North/West"},
    "Moonee Ponds":         {"price": "65.00", "zone": "Inner North/West"},
    "Niddrie":              {"price": "60.00", "zone": "Inner North/West"},
    "Strathmore":           {"price": "60.00", "zone": "Inner North/West"},
    "Tullamarine":          {"price": "60.00", "zone": "Inner North/West"},
    "Westmeadows":          {"price": "60.00", "zone": "Inner North/West"},

    # ── Central Melbourne (~20-26 km) ─────────────────────────────────────
    "Brunswick":            {"price": "75.00", "zone": "Central Melbourne"},
    "Carlton":              {"price": "75.00", "zone": "Central Melbourne"},
    "Coburg":               {"price": "72.00", "zone": "Central Melbourne"},
    "Collingwood":          {"price": "75.00", "zone": "Central Melbourne"},
    "Docklands":            {"price": "60.00", "zone": "Central Melbourne"},
    "Fitzroy":              {"price": "76.00", "zone": "Central Melbourne"},
    "Melbourne CBD":        {"price": "75.00", "zone": "Central Melbourne"},
    "Richmond":             {"price": "78.00", "zone": "Central Melbourne"},
    "Southbank":            {"price": "75.00", "zone": "Central Melbourne"},

    # ── Inner North (~22-28 km) ───────────────────────────────────────────
    "Batman":               {"price": "60.00", "zone": "Inner North"},
    "Heidelberg":           {"price": "82.00", "zone": "Inner North"},
    "Ivanhoe":              {"price": "82.00", "zone": "Inner North"},
    "Northcote":            {"price": "78.00", "zone": "Inner North"},
    "Preston":              {"price": "78.00", "zone": "Inner North"},
    "Reservoir":            {"price": "76.00", "zone": "Inner North"},
    "Thornbury":            {"price": "65.00", "zone": "Inner North"},

    # ── Inner South (~21-35 km) ───────────────────────────────────────────
    "Albert Park":          {"price": "70.00", "zone": "Inner South"},
    "Armadale":             {"price": "80.00", "zone": "Inner South"},
    "Brighton":             {"price": "88.00", "zone": "Inner South"},
    "Brighton East":        {"price": "100.00", "zone": "Inner South"},
    "Hampton":              {"price": "100.00", "zone": "Inner South"},
    "Hawksburn":            {"price": "80.00", "zone": "Inner South"},
    "Middle Park":          {"price": "75.00", "zone": "Inner South"},
    "Port Melbourne":       {"price": "65.00", "zone": "Inner South"},
    "Prahran":              {"price": "82.00", "zone": "Inner South"},
    "South Melbourne":      {"price": "65.00", "zone": "Inner South"},
    "South Yarra":          {"price": "82.00", "zone": "Inner South"},
    "St Kilda":             {"price": "85.00", "zone": "Inner South"},
    "Windsor":              {"price": "82.00", "zone": "Inner South"},

    # ── Inner East (~27-32 km) ────────────────────────────────────────────
    "Balwyn":               {"price": "85.00", "zone": "Inner East"},
    "Balwyn North":         {"price": "85.00", "zone": "Inner East"},
    "Burwood":              {"price": "85.00", "zone": "Inner East"},
    "Camberwell":           {"price": "90.00", "zone": "Inner East"},
    "Caulfield":            {"price": "90.00", "zone": "Inner East"},
    "Caulfield North":      {"price": "85.00", "zone": "Inner East"},
    "Caulfield South":      {"price": "95.00", "zone": "Inner East"},
    "Glen Iris":            {"price": "85.00", "zone": "Inner East"},
    "Hawthorn":             {"price": "85.00", "zone": "Inner East"},
    "Kooyong":              {"price": "85.00", "zone": "Inner East"},
    "Malvern":              {"price": "80.00", "zone": "Inner East"},
    "Malvern East":         {"price": "90.00", "zone": "Inner East"},
    "Oakleigh":             {"price": "88.00", "zone": "Inner East"},
    "Toorak":               {"price": "88.00", "zone": "Inner East"},

    # ── North-East (~26-37 km) ────────────────────────────────────────────
    "Diamond Creek":        {"price": "98.00", "zone": "North-East"},
    "Doncaster East":       {"price": "95.00", "zone": "North-East"},
    "Eltham":               {"price": "92.00", "zone": "Eastern Suburbs"},
    "Greensborough":        {"price": "90.00", "zone": "Eastern Suburbs"},
    "Lower Plenty":         {"price": "90.00", "zone": "North-East"},
    "Macleod":              {"price": "80.00", "zone": "North-East"},
    "Montmorency":          {"price": "95.00", "zone": "North-East"},
    "Park Orchards":        {"price": "105.00", "zone": "North-East"},
    "Plenty":               {"price": "90.00", "zone": "North-East"},
    "Rosanna":              {"price": "80.00", "zone": "North-East"},
    "Templestowe":          {"price": "85.00", "zone": "North-East"},
    "Templestowe Lower":    {"price": "80.00", "zone": "North-East"},
    "Viewbank":             {"price": "80.00", "zone": "North-East"},
    "Warrandyte":           {"price": "110.00", "zone": "North-East"},
    "Warrandyte South":     {"price": "110.00", "zone": "North-East"},
    "Watsonia":             {"price": "80.00", "zone": "North-East"},
    "Yarrambat":            {"price": "95.00", "zone": "North-East"},

    # ── Eastern Suburbs (~29-45 km) ───────────────────────────────────────
    "Bayswater":            {"price": "102.00", "zone": "Eastern Suburbs"},
    "Blackburn":            {"price": "95.00", "zone": "Eastern Suburbs"},
    "Blackburn North":      {"price": "95.00", "zone": "Eastern Suburbs"},
    "Blackburn South":      {"price": "100.00", "zone": "Eastern Suburbs"},
    "Boronia":              {"price": "102.00", "zone": "Eastern Suburbs"},
    "Box Hill":             {"price": "92.00", "zone": "Eastern Suburbs"},
    "Burwood East":         {"price": "95.00", "zone": "Eastern Suburbs"},
    "Croydon":              {"price": "95.00", "zone": "Eastern Suburbs"},
    "Croydon North":        {"price": "120.00", "zone": "Eastern Suburbs"},
    "Croydon South":        {"price": "120.00", "zone": "Eastern Suburbs"},
    "Doncaster":            {"price": "90.00", "zone": "Eastern Suburbs"},
    "Forest Hill":          {"price": "105.00", "zone": "Eastern Suburbs"},
    "Glen Waverley":        {"price": "90.00", "zone": "Eastern Suburbs"},
    "Heathmont":            {"price": "120.00", "zone": "Eastern Suburbs"},
    "Lilydale":             {"price": "110.00", "zone": "Eastern Suburbs"},
    "Mitcham":              {"price": "110.00", "zone": "Eastern Suburbs"},
    "Mont Albert":          {"price": "95.00", "zone": "Eastern Suburbs"},
    "Mooroolbark":          {"price": "105.00", "zone": "Eastern Suburbs"},
    "Mount Waverley":       {"price": "95.00", "zone": "Eastern Suburbs"},
    "Notting Hill":         {"price": "100.00", "zone": "Eastern Suburbs"},
    "Nunawading":           {"price": "100.00", "zone": "Eastern Suburbs"},
    "Ringwood":             {"price": "95.00", "zone": "Eastern Suburbs"},
    "Ringwood East":        {"price": "125.00", "zone": "Eastern Suburbs"},
    "Vermont":              {"price": "115.00", "zone": "Eastern Suburbs"},
    "Wantirna":             {"price": "110.00", "zone": "Eastern Suburbs"},
    "Wantirna South":       {"price": "115.00", "zone": "Eastern Suburbs"},

    # ── Northern Suburbs (~12-33 km) ──────────────────────────────────────
    "Broadmeadows":         {"price": "60.00", "zone": "Northern Suburbs"},
    "Bundoora":             {"price": "85.00", "zone": "Northern Suburbs"},
    "Campbellfield":        {"price": "60.00", "zone": "Northern Suburbs"},
    "Coburg North":         {"price": "60.00", "zone": "Northern Suburbs"},
    "Craigieburn":          {"price": "72.00", "zone": "Northern Suburbs"},
    "Dallas":               {"price": "60.00", "zone": "Northern Suburbs"},
    "Doreen":               {"price": "100.00", "zone": "Northern Suburbs"},
    "Epping":               {"price": "85.00", "zone": "Northern Suburbs"},
    "Fawkner":              {"price": "60.00", "zone": "Northern Suburbs"},
    "Glenroy":              {"price": "60.00", "zone": "Northern Suburbs"},
    "Greenvale":            {"price": "60.00", "zone": "Northern Suburbs"},
    "Kingsbury":            {"price": "70.00", "zone": "Northern Suburbs"},
    "Lalor":                {"price": "65.00", "zone": "Northern Suburbs"},
    "Meadow Heights":       {"price": "60.00", "zone": "Northern Suburbs"},
    "Mernda":               {"price": "95.00", "zone": "Northern Suburbs"},
    "Mill Park":            {"price": "88.00", "zone": "Northern Suburbs"},
    "Oak Park":             {"price": "60.00", "zone": "Northern Suburbs"},
    "Pascoe Vale":          {"price": "60.00", "zone": "Northern Suburbs"},
    "Roxburgh Park":        {"price": "70.00", "zone": "Northern Suburbs"},
    "South Morang":         {"price": "90.00", "zone": "Northern Suburbs"},
    "Thomastown":           {"price": "65.00", "zone": "Northern Suburbs"},

    # ── Western Suburbs (~14-43 km) ───────────────────────────────────────
    "Albanvale":            {"price": "60.00", "zone": "Western Suburbs"},
    "Altona":               {"price": "82.00", "zone": "Western Suburbs"},
    "Avondale Heights":     {"price": "60.00", "zone": "Western Suburbs"},
    "Caroline Springs":     {"price": "75.00", "zone": "Western Suburbs"},
    "Deer Park":            {"price": "65.00", "zone": "Western Suburbs"},
    "Derrimut":             {"price": "65.00", "zone": "Western Suburbs"},
    "Footscray":            {"price": "78.00", "zone": "Western Suburbs"},
    "Hillside":             {"price": "60.00", "zone": "Western Suburbs"},
    "Hoppers Crossing":     {"price": "92.00", "zone": "Western Suburbs"},
    "Kings Park":           {"price": "60.00", "zone": "Western Suburbs"},
    "Laverton":             {"price": "85.00", "zone": "Western Suburbs"},
    "Manor Lakes":          {"price": "130.00", "zone": "Western Suburbs"},
    "Maribyrnong":          {"price": "60.00", "zone": "Western Suburbs"},
    "Melton South":         {"price": "100.00", "zone": "Western Suburbs"},
    "Point Cook":           {"price": "90.00", "zone": "Western Suburbs"},
    "St Albans":            {"price": "60.00", "zone": "Western Suburbs"},
    "Sunshine":             {"price": "60.00", "zone": "Western Suburbs"},
    "Sunshine North":       {"price": "60.00", "zone": "Western Suburbs"},
    "Sunshine West":        {"price": "60.00", "zone": "Western Suburbs"},
    "Tarneit":              {"price": "90.00", "zone": "Western Suburbs"},
    "Taylors Hill":         {"price": "60.00", "zone": "Western Suburbs"},
    "Taylors Lakes":        {"price": "60.00", "zone": "Western Suburbs"},
    "Truganina":            {"price": "85.00", "zone": "Western Suburbs"},
    "Werribee":             {"price": "92.00", "zone": "Western Suburbs"},
    "Williams Landing":     {"price": "85.00", "zone": "Western Suburbs"},
    "Williamstown":         {"price": "82.00", "zone": "Western Suburbs"},
    "Wyndham Vale":         {"price": "115.00", "zone": "Western Suburbs"},

    # ── South-East (~30-45 km) ────────────────────────────────────────────
    "Bangholme":            {"price": "135.00", "zone": "South-East"},
    "Beaumaris":            {"price": "115.00", "zone": "South-East"},
    "Bentleigh":            {"price": "100.00", "zone": "South-East"},
    "Bentleigh East":       {"price": "100.00", "zone": "South-East"},
    "Black Rock":           {"price": "115.00", "zone": "South-East"},
    "Carnegie":             {"price": "95.00", "zone": "South-East"},
    "Cheltenham":           {"price": "95.00", "zone": "South-East"},
    "Clayton":              {"price": "110.00", "zone": "South-East"},
    "Dandenong":            {"price": "108.00", "zone": "South-East"},
    "Dingley Village":      {"price": "110.00", "zone": "South-East"},
    "Frankston":            {"price": "115.00", "zone": "South-East"},
    "Heatherton":           {"price": "100.00", "zone": "South-East"},
    "Huntingdale":          {"price": "115.00", "zone": "South-East"},
    "Keysborough":          {"price": "130.00", "zone": "South-East"},
    "Knox":                 {"price": "105.00", "zone": "South-East"},
    "Lysterfield":          {"price": "130.00", "zone": "South-East"},
    "McKinnon":             {"price": "95.00", "zone": "South-East"},
    "Mentone":              {"price": "110.00", "zone": "South-East"},
    "Moorabbin":            {"price": "95.00", "zone": "South-East"},
    "Mordialloc":           {"price": "115.00", "zone": "South-East"},
    "Mulgrave":             {"price": "120.00", "zone": "South-East"},
    "Murrumbeena":          {"price": "90.00", "zone": "South-East"},
    "Noble Park":           {"price": "130.00", "zone": "South-East"},
    "Oakleigh East":        {"price": "110.00", "zone": "South-East"},
    "Oakleigh South":       {"price": "115.00", "zone": "South-East"},
    "Ormond":               {"price": "95.00", "zone": "South-East"},
    "Parkdale":             {"price": "110.00", "zone": "South-East"},
    "Rowville":             {"price": "130.00", "zone": "South-East"},
    "Sandringham":          {"price": "110.00", "zone": "South-East"},
    "Springvale":           {"price": "105.00", "zone": "South-East"},
    "Springvale South":     {"price": "130.00", "zone": "South-East"},
    "Wheelers Hill":        {"price": "125.00", "zone": "South-East"},

    # ── Regional (65 km+) ─────────────────────────────────────────────────
    "Geelong":              {"price": "165.00", "zone": "Regional"},
    "Mornington":           {"price": "155.00", "zone": "Regional"},
}


class Command(BaseCommand):
    help = (
        "Load all Melbourne suburbs into RegionSuburb. "
        "Idempotent — safe to re-run on production. "
        "Uses get_or_create by (region, name); never duplicates."
    )

    def handle(self, *args, **options):
        from regions.models import Region, RegionSuburb

        # ── 1. Get or create the Melbourne region ─────────────────────────
        melbourne, region_created = Region.objects.get_or_create(
            slug="melbourne",
            defaults={
                "name": "Melbourne",
                "state_code": "VIC",
                "timezone": "Australia/Melbourne",
                "is_active": True,
            },
        )
        if region_created:
            self.stdout.write(self.style.WARNING("Created Melbourne region (was missing)."))
        else:
            self.stdout.write(f"Melbourne region found (pk={melbourne.pk}).")

        # ── 2. Load suburbs ───────────────────────────────────────────────
        created_count = 0
        skipped_count = 0
        total = len(SUBURBS)

        for i, (name, data) in enumerate(SUBURBS.items(), start=1):
            price = Decimal(data["price"])
            zone = data["zone"]
            price_int = int(price)

            obj, was_created = RegionSuburb.objects.get_or_create(
                region=melbourne,
                name=name,
                defaults={
                    "slug": name.lower().replace(" ", "-").replace("'", ""),
                    "price": price,
                    "zone": zone,
                    "is_active": True,
                    "meta_title": f"{name} Airport Shuttle | EasyGo Melbourne",
                    "meta_description": (
                        f"Private airport shuttle from {name} to Melbourne Airport (MEL). "
                        f"Fixed price from ${price_int} per vehicle. "
                        "Door-to-door, meet & greet, flight tracking included. Book online."
                    ),
                },
            )

            if was_created:
                created_count += 1
                self.stdout.write(f"  [{i:>3}/{total}] Created:  {name} ({zone}) — ${price_int}")
            else:
                skipped_count += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(f"  [{i:>3}/{total}] Exists:   {name}")

        # ── 3. Summary ────────────────────────────────────────────────────
        final_count = RegionSuburb.objects.filter(
            region=melbourne, is_active=True, is_pinned=False
        ).count()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created_count}  |  Already existed: {skipped_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Total active Melbourne suburbs in DB: {final_count}"
        ))
