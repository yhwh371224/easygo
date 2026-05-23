from django.db import migrations

NEW_TITLE = "Melbourne Airport Transfer & Shuttle | Fixed Price | EasyGo"
NEW_DESC = (
    "Melbourne airport transfer & Melbourne airport shuttle. "
    "Private 8-13 seater for CBD, Northern & Western suburbs. "
    "Fixed prices, no hidden fees. 24/7."
)

OLD_TITLE = "Melbourne Airport Transfer | Fixed Price & Private (8-13 Seater) | EasyGo"
OLD_DESC = (
    "Book your Melbourne airport transfer now! Private pickup service with 8-13 seater vehicles. "
    "Serving Melbourne CBD, Northern Suburbs & Western Melbourne. Fixed prices, no hidden fees. Available 24/7"
)


def update_melbourne_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    Region.objects.filter(slug="melbourne").update(
        meta_title=NEW_TITLE,
        meta_description=NEW_DESC,
    )


def reverse_melbourne_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    Region.objects.filter(slug="melbourne").update(
        meta_title=OLD_TITLE,
        meta_description=OLD_DESC,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0044_terminalpickuppoint_is_default_point_is_default_second"),
    ]

    operations = [
        migrations.RunPython(update_melbourne_seo, reverse_melbourne_seo),
    ]
