from django.db import migrations

MELBOURNE = [
    ("Altona",    1, "/static/basecamp/photos/maps/altona.webp"),
    ("Bayswater", 2, "/static/basecamp/photos/maps/bayswater.webp"),
    ("Boronia",   3, "/static/basecamp/photos/maps/boronia.webp"),
    ("Box Hill",  4, "/static/basecamp/photos/maps/box-hill.webp"),
    ("Brighton",  5, "/static/basecamp/photos/maps/brighton.webp"),
    ("Brunswick", 6, "/static/basecamp/photos/maps/brunswick.webp"),
]

BRISBANE = [
    ("Brisbane CBD",     1, "/static/basecamp/photos/maps/brisbane-cbd.webp"),
    ("Fortitude Valley", 2, "/static/basecamp/photos/maps/fortitude-valley.webp"),
    ("South Brisbane",   3, "/static/basecamp/photos/maps/south-brisbane.webp"),
    ("Chermside",        4, "/static/basecamp/photos/maps/chermside.webp"),
    ("Sunnybank",        5, "/static/basecamp/photos/maps/sunnybank.webp"),
    ("Indooroopilly",    6, "/static/basecamp/photos/maps/indooroopilly.webp"),
]

GOLD_COAST = [
    ("Surfers Paradise", 1, "/static/basecamp/photos/maps/surfers-paradise.webp"),
    ("Broadbeach",       2, "/static/basecamp/photos/maps/broadbeach.webp"),
    ("Southport",        3, "/static/basecamp/photos/maps/southport.webp"),
    ("Burleigh Heads",   4, "/static/basecamp/photos/maps/burleigh-heads.webp"),
    ("Coolangatta",      5, "/static/basecamp/photos/maps/coolangatta.webp"),
    ("Robina",           6, "/static/basecamp/photos/maps/robina.webp"),
]

REGIONS = [
    ("melbourne",  MELBOURNE),
    ("brisbane",   BRISBANE),
    ("gold-coast", GOLD_COAST),
]


def seed_carousel(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    RegionSuburb = apps.get_model("regions", "RegionSuburb")

    for region_slug, suburbs in REGIONS:
        try:
            region = Region.objects.get(slug=region_slug)
        except Region.DoesNotExist:
            continue
        for name, order, image in suburbs:
            RegionSuburb.objects.filter(region=region, name=name).update(
                is_featured=True,
                featured_order=order,
                carousel_image=image,
            )


def unseed_carousel(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    RegionSuburb = apps.get_model("regions", "RegionSuburb")

    for region_slug, suburbs in REGIONS:
        try:
            region = Region.objects.get(slug=region_slug)
        except Region.DoesNotExist:
            continue
        names = [name for name, _, _ in suburbs]
        RegionSuburb.objects.filter(region=region, name__in=names).update(
            is_featured=False,
            featured_order=999,
            carousel_image="",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0027_backfill_carousel_image_paths"),
    ]

    operations = [
        migrations.RunPython(seed_carousel, reverse_code=unseed_carousel),
    ]
