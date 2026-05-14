from django.db import migrations


OLD_PREFIX = "/static/basecamp/photos/"
NEW_PREFIX = "/static/basecamp/photos/maps/"


def move_carousel_images_to_maps(apps, schema_editor):
    RegionSuburb = apps.get_model("regions", "RegionSuburb")
    qs = RegionSuburb.objects.filter(
        carousel_image__startswith=OLD_PREFIX
    ).exclude(
        carousel_image__startswith=NEW_PREFIX
    )
    for suburb in qs:
        suburb.carousel_image = suburb.carousel_image.replace(OLD_PREFIX, NEW_PREFIX)
        suburb.save(update_fields=["carousel_image"])


def reverse_carousel_images(apps, schema_editor):
    RegionSuburb = apps.get_model("regions", "RegionSuburb")
    qs = RegionSuburb.objects.filter(carousel_image__startswith=NEW_PREFIX)
    for suburb in qs:
        suburb.carousel_image = suburb.carousel_image.replace(NEW_PREFIX, OLD_PREFIX)
        suburb.save(update_fields=["carousel_image"])


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0026_terminal_icon_note_sort_order"),
    ]

    operations = [
        migrations.RunPython(
            move_carousel_images_to_maps,
            reverse_code=reverse_carousel_images,
        ),
    ]
