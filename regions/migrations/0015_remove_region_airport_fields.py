from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("regions", "0014_backfill_airports_from_region_fields"),
    ]

    operations = [
        migrations.RemoveField(model_name="region", name="airport_code"),
        migrations.RemoveField(model_name="region", name="airport_name"),
        migrations.RemoveField(model_name="region", name="airport_lat"),
        migrations.RemoveField(model_name="region", name="airport_lng"),
    ]

