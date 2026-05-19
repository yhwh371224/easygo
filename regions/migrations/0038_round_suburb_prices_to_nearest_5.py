from django.db import migrations
from decimal import Decimal, ROUND_HALF_UP


def round_to_nearest_5(apps, schema_editor):
    RegionSuburb = apps.get_model('regions', 'RegionSuburb')
    to_update = []
    for suburb in RegionSuburb.objects.select_related('region').all():
        price = float(suburb.price)
        rounded = round(price / 5) * 5
        new_price = Decimal(str(rounded)).quantize(Decimal('0.01'))
        if new_price != suburb.price:
            suburb.price = new_price
            to_update.append(suburb)
    if to_update:
        RegionSuburb.objects.bulk_update(to_update, ['price'])


def reverse_round(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0037_regionsuburb_add_lat_lng'),
    ]

    operations = [
        migrations.RunPython(round_to_nearest_5, reverse_round),
    ]
