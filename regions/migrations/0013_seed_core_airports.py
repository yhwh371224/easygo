from django.db import migrations


def seed_core_airports(apps, schema_editor):
    Country = apps.get_model("regions", "Country")
    Airport = apps.get_model("regions", "Airport")
    Terminal = apps.get_model("regions", "Terminal")
    Region = apps.get_model("regions", "Region")

    australia, _ = Country.objects.get_or_create(name="Australia")

    # Seed only a small core set (safe: idempotent get_or_create).
    airports = [
        {"code": "SYD", "city": "Sydney"},
        {"code": "MEL", "city": "Melbourne"},
        {"code": "BNE", "city": "Brisbane"},
    ]

    for a in airports:
        airport, _ = Airport.objects.get_or_create(
            code=a["code"],
            defaults={"country": australia, "city": a["city"]},
        )

        # Backward compatibility via DB data: terminal names exist in DB and
        # are derived from the authoritative Airport.city (no city-specific code paths).
        Terminal.objects.get_or_create(airport=airport, type="intl", name=f"{airport.city} Int'l Airport")
        Terminal.objects.get_or_create(airport=airport, type="domestic", name=f"{airport.city} Domestic Airport")

        # Link any existing Region that matches airport_code.
        for region in Region.objects.filter(airport_code=airport.code):
            # M2M safe-add (no duplicates)
            region.airports.add(airport)


def unseed_core_airports(apps, schema_editor):
    # Non-destructive rollback: do not delete production data.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("regions", "0012_airport_terminal_models"),
    ]

    operations = [
        migrations.RunPython(seed_core_airports, reverse_code=unseed_core_airports),
    ]

