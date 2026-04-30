from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0011_seed_melbourne_airport_pinned"),
    ]

    operations = [
        migrations.CreateModel(
            name="Country",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Airport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("city", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=10, unique=True)),
                (
                    "country",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="airports", to="regions.country"),
                ),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="Terminal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("type", models.CharField(choices=[("intl", "International"), ("domestic", "Domestic")], max_length=10)),
                (
                    "airport",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="terminals", to="regions.airport"),
                ),
            ],
            options={
                "ordering": ["airport__code", "type", "name"],
                "unique_together": {("airport", "type", "name")},
            },
        ),
        migrations.AddField(
            model_name="region",
            name="airports",
            field=models.ManyToManyField(blank=True, related_name="regions", to="regions.airport"),
        ),
    ]

