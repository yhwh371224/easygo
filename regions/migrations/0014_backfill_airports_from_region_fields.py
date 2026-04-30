from decimal import Decimal

from django.db import migrations, models


def backfill_airports_from_regions(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    Airport = apps.get_model("regions", "Airport")

    for region in Region.objects.all():
        # Legacy region fields still exist at this point in migration history.
        code = getattr(region, "airport_code", None)
        if not code:
            continue

        airport = Airport.objects.filter(code=code).first()
        if not airport:
            continue

        # Preserve legacy metadata by moving it onto Airport (single source of truth).
        airport.name = getattr(region, "airport_name", "") or airport.name
        airport.lat = getattr(region, "airport_lat", None) if getattr(region, "airport_lat", None) is not None else airport.lat
        airport.lng = getattr(region, "airport_lng", None) if getattr(region, "airport_lng", None) is not None else airport.lng
        airport.save(update_fields=["name", "lat", "lng"])

        # Ensure Region <-> Airport relationship exists.
        try:
            region.airports.add(airport)
        except Exception:
            # If M2M table isn't ready for some reason, fail-safe: skip.
            pass


def noop_reverse(apps, schema_editor):
    # Non-destructive rollback: keep data.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("regions", "0013_seed_core_airports"),
    ]

    operations = [
        migrations.AddField(
            model_name="airport",
            name="name",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="airport",
            name="lat",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="airport",
            name="lng",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
        migrations.RunPython(backfill_airports_from_regions, reverse_code=noop_reverse),
    ]

