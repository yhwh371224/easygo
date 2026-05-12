from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Adds TerminalPickupPoint and PickupPointMap; drops the never-migrated
    pickup_instruction field and TerminalMap model (both existed only in
    models.py and have no corresponding DB columns or table).
    """

    dependencies = [
        ("regions", "0022_regionsuburb_carousel_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="TerminalPickupPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("instruction", models.TextField(blank=True)),
                (
                    "terminal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pickup_points",
                        to="regions.terminal",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PickupPointMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("url", models.URLField()),
                (
                    "pickup_point",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="maps",
                        to="regions.terminalpickuppoint",
                    ),
                ),
            ],
            options={
                "ordering": ["pickup_point", "title"],
            },
        ),
    ]
