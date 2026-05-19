from decimal import Decimal
from django.db import migrations


TERMINAL_DATA = [
    {
        "name": "Brisbane Cruise Terminal",
        "lat": Decimal("-27.433400"),
        "lng": Decimal("153.060100"),
        "distance_km": Decimal("17.0"),
    },
    {
        "name": "Webb Dock Cruise Terminal",
        "lat": Decimal("-37.831300"),
        "lng": Decimal("144.912300"),
        "distance_km": Decimal("26.0"),
    },
    {
        "name": "Station Pier Cruise Terminal",
        "lat": Decimal("-37.837600"),
        "lng": Decimal("144.918700"),
        "distance_km": Decimal("25.0"),
    },
    {
        "name": "Overseas Cruise Terminal",
        "lat": Decimal("-33.857100"),
        "lng": Decimal("151.209600"),
        "distance_km": Decimal("10.0"),
    },
    {
        "name": "WhiteBay Cruise Terminal",
        "lat": Decimal("-33.860500"),
        "lng": Decimal("151.184300"),
        "distance_km": Decimal("11.0"),
    },
]


def populate_cruise_terminals(apps, schema_editor):
    CruiseTerminal = apps.get_model("regions", "CruiseTerminal")
    for data in TERMINAL_DATA:
        base_price = (data["distance_km"] * Decimal("3")).quantize(Decimal("0.01"))
        CruiseTerminal.objects.filter(name=data["name"]).update(
            lat=data["lat"],
            lng=data["lng"],
            distance_km=data["distance_km"],
            base_price=base_price,
        )


def reverse_populate(apps, schema_editor):
    CruiseTerminal = apps.get_model("regions", "CruiseTerminal")
    CruiseTerminal.objects.all().update(lat=None, lng=None, distance_km=None, base_price=None)


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0041_cruiseterminal_base_price_cruiseterminal_distance_km_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_cruise_terminals, reverse_populate),
    ]
