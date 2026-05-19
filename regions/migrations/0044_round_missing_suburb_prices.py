from decimal import Decimal
from django.db import migrations


SUBURB_DATA = [
    ("Sydney",      "Campsie",          Decimal("70.00")),
    ("Sydney",      "Clemton Park",     Decimal("55.00")),
    ("Sydney",      "Earlwood",         Decimal("45.00")),
    ("Sydney",      "Hurlstaon Park",   Decimal("70.00")),
    ("Sydney",      "Kogarah",          Decimal("60.00")),
    ("Sydney",      "North Rocks",      Decimal("115.00")),
    ("Sydney",      "Oatley",           Decimal("70.00")),
    ("Melbourne",   "Berwick",          Decimal("230.00")),
    ("Melbourne",   "Hotels In CBD",    Decimal("85.00")),
    ("Melbourne",   "Narre Warren",     Decimal("225.00")),
    ("Gold Coast",  "Hotels in CBD",    Decimal("90.00")),
    ("Brisbane",    "Hotels in CBD",    Decimal("75.00")),
]


def round_prices(apps, schema_editor):
    RegionSuburb = apps.get_model("regions", "RegionSuburb")
    for region_name, suburb_name, price in SUBURB_DATA:
        RegionSuburb.objects.filter(
            region__name=region_name,
            name=suburb_name,
        ).update(price=price)


def reverse_round(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0043_populate_missing_suburb_distance_price"),
    ]

    operations = [
        migrations.RunPython(round_prices, reverse_round),
    ]
