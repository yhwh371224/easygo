from decimal import Decimal
from django.db import migrations


SUBURB_DATA = [
    # (region_name, suburb_name, distance_km, price)
    ("Sydney",      "Campsie",          Decimal("14.0"), Decimal("72.00")),
    ("Sydney",      "Clemton Park",     Decimal("8.0"),  Decimal("54.00")),
    ("Sydney",      "Earlwood",         Decimal("5.0"),  Decimal("45.00")),
    ("Sydney",      "Hurlstaon Park",   Decimal("13.0"), Decimal("69.00")),
    ("Sydney",      "Kogarah",          Decimal("10.0"), Decimal("60.00")),
    ("Sydney",      "North Rocks",      Decimal("31.0"), Decimal("113.00")),
    ("Sydney",      "Oatley",           Decimal("14.0"), Decimal("72.00")),
    ("Melbourne",   "Berwick",          Decimal("70.0"), Decimal("230.00")),
    ("Melbourne",   "Hotels In CBD",    Decimal("22.0"), Decimal("86.00")),
    ("Melbourne",   "Narre Warren",     Decimal("68.0"), Decimal("224.00")),
    ("Gold Coast",  "Hotels in CBD",    Decimal("23.0"), Decimal("89.00")),
    ("Brisbane",    "Hotels in CBD",    Decimal("15.0"), Decimal("75.00")),
]


def populate_missing_suburbs(apps, schema_editor):
    RegionSuburb = apps.get_model("regions", "RegionSuburb")
    for region_name, suburb_name, distance_km, price in SUBURB_DATA:
        RegionSuburb.objects.filter(
            region__name=region_name,
            name=suburb_name,
        ).update(distance_km=distance_km, price=price)


def reverse_populate(apps, schema_editor):
    RegionSuburb = apps.get_model("regions", "RegionSuburb")
    for region_name, suburb_name, _, _ in SUBURB_DATA:
        RegionSuburb.objects.filter(
            region__name=region_name,
            name=suburb_name,
        ).update(distance_km=None, price=None)


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0042_populate_cruise_terminal_coords"),
    ]

    operations = [
        migrations.RunPython(populate_missing_suburbs, reverse_populate),
    ]
