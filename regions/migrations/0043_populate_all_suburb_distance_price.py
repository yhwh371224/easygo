from decimal import Decimal
from django.db import migrations


SUBURB_DATA = [
    # (region_name, suburb_name, distance_km, price)
    # --- Brisbane ---
    ("Brisbane", "Alderley",             Decimal("14.52"), Decimal("90.00")),
    ("Brisbane", "Arana Hills",          Decimal("19.30"), Decimal("100.00")),
    ("Brisbane", "Bald Hills",           Decimal("21.82"), Decimal("95.00")),
    ("Brisbane", "Brighton",             Decimal("20.45"), Decimal("100.00")),
    ("Brisbane", "Caboolture",           Decimal("48.84"), Decimal("130.00")),
    ("Brisbane", "Carseldine",           Decimal("21.83"), Decimal("90.00")),
    ("Brisbane", "Dakabin",              Decimal("35.17"), Decimal("110.00")),
    ("Brisbane", "Deagon",               Decimal("18.36"), Decimal("90.00")),
    ("Brisbane", "Deception Bay",        Decimal("36.59"), Decimal("120.00")),
    ("Brisbane", "Fairfield",            Decimal("20.28"), Decimal("90.00")),
    ("Brisbane", "Ferny Hills",          Decimal("20.74"), Decimal("100.00")),
    ("Brisbane", "Hotels in CBD",        Decimal("15.00"), Decimal("75.00")),
    ("Brisbane", "Jindalee",             Decimal("29.48"), Decimal("100.00")),
    ("Brisbane", "Kangaroo Point",       Decimal("18.36"), Decimal("80.00")),
    ("Brisbane", "Kedron",               Decimal("11.46"), Decimal("85.00")),
    ("Brisbane", "Kenmore Hills",        Decimal("28.68"), Decimal("105.00")),
    ("Brisbane", "Kingston",             Decimal("36.46"), Decimal("120.00")),
    ("Brisbane", "Loganholme",           Decimal("41.83"), Decimal("120.00")),
    ("Brisbane", "Meadowbrook",          Decimal("36.30"), Decimal("120.00")),
    ("Brisbane", "Middle Park",          Decimal("31.49"), Decimal("105.00")),
    ("Brisbane", "Morayfield",           Decimal("46.72"), Decimal("120.00")),
    ("Brisbane", "Narangba",             Decimal("40.23"), Decimal("115.00")),
    ("Brisbane", "Norman Park",          Decimal("16.02"), Decimal("90.00")),
    ("Brisbane", "North Lakes",          Decimal("34.98"), Decimal("115.00")),
    ("Brisbane", "Riverhills",           Decimal("33.55"), Decimal("110.00")),
    ("Brisbane", "Rosalie",              Decimal("17.52"), Decimal("85.00")),
    ("Brisbane", "Seventeen Mile Rocks", Decimal("29.50"), Decimal("105.00")),
    ("Brisbane", "Shailer Park",         Decimal("37.72"), Decimal("120.00")),
    ("Brisbane", "Sinnamon Park",        Decimal("28.88"), Decimal("100.00")),
    ("Brisbane", "Slacks Creek",         Decimal("33.98"), Decimal("120.00")),
    ("Brisbane", "The Gap",              Decimal("23.93"), Decimal("100.00")),
    ("Brisbane", "Underwood",            Decimal("27.62"), Decimal("110.00")),
    ("Brisbane", "Upper Kedron",         Decimal("22.84"), Decimal("105.00")),
    ("Brisbane", "Wavell Heights",       Decimal("10.19"), Decimal("80.00")),
    ("Brisbane", "Windsor",              Decimal("11.36"), Decimal("80.00")),
    ("Brisbane", "Woodridge",            Decimal("33.61"), Decimal("120.00")),
    # --- Gold Coast ---
    ("Gold Coast", "Banora Point",       Decimal("12.06"), Decimal("65.00")),
    ("Gold Coast", "Bilambil Heights",   Decimal("12.85"), Decimal("70.00")),
    ("Gold Coast", "Canungra",           Decimal("40.01"), Decimal("120.00")),
    ("Gold Coast", "Chevron Island",     Decimal("27.14"), Decimal("90.00")),
    ("Gold Coast", "Gold Coast Airport", Decimal("4.21"),  Decimal("0.00")),
    ("Gold Coast", "Hotels in CBD",      Decimal("23.00"), Decimal("90.00")),
    ("Gold Coast", "Isle of Capri",      Decimal("26.70"), Decimal("90.00")),
    ("Gold Coast", "Kirra",              Decimal("5.71"),  Decimal("55.00")),
    ("Gold Coast", "Nobby Beach",        Decimal("14.74"), Decimal("80.00")),
    ("Gold Coast", "Sanctuary Cove",     Decimal("48.89"), Decimal("110.00")),
    ("Gold Coast", "Tamborine Mountain", Decimal("56.13"), Decimal("125.00")),
    ("Gold Coast", "Tweed Heads",        Decimal("7.69"),  Decimal("65.00")),
    ("Gold Coast", "Tweed Heads South",  Decimal("8.72"),  Decimal("60.00")),
    ("Gold Coast", "Tweed Heads West",   Decimal("8.70"),  Decimal("70.00")),
    ("Gold Coast", "West Burleigh",      Decimal("10.99"), Decimal("80.00")),
    # --- Melbourne ---
    ("Melbourne", "Berwick",             Decimal("70.00"), Decimal("230.00")),
    ("Melbourne", "Hotels In CBD",       Decimal("22.00"), Decimal("85.00")),
    ("Melbourne", "Narre Warren",        Decimal("68.00"), Decimal("225.00")),
    # --- Sydney ---
    ("Sydney", "Campsie",               Decimal("14.00"), Decimal("70.00")),
    ("Sydney", "Clemton Park",          Decimal("8.00"),  Decimal("55.00")),
    ("Sydney", "Earlwood",              Decimal("5.00"),  Decimal("45.00")),
    ("Sydney", "Hotels In CBD",         Decimal("11.63"), Decimal("60.00")),
    ("Sydney", "Hurlstaon Park",        Decimal("13.00"), Decimal("70.00")),
    ("Sydney", "Kogarah",               Decimal("10.00"), Decimal("60.00")),
    ("Sydney", "North Rocks",           Decimal("31.00"), Decimal("115.00")),
    ("Sydney", "Oatley",                Decimal("14.00"), Decimal("70.00")),
]


def populate_suburbs(apps, schema_editor):
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
        migrations.RunPython(populate_suburbs, reverse_populate),
    ]
