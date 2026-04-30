from django.db import migrations, models
import django.db.models.deletion


def backfill_primary_airport(apps, schema_editor):
    Region = apps.get_model("regions", "Region")

    for region in Region.objects.all():
        if getattr(region, "primary_airport_id", None):
            continue
        airports = list(region.airports.all()[:2])
        if len(airports) == 1:
            region.primary_airport = airports[0]
            region.save(update_fields=["primary_airport"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("regions", "0015_remove_region_airport_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="region",
            name="primary_airport",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="primary_for_regions",
                to="regions.airport",
            ),
        ),
        migrations.RunPython(backfill_primary_airport, reverse_code=noop_reverse),
    ]

