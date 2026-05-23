from django.db import migrations

NEW_TITLE = "Brisbane Airport Transfer & Shuttle | Fixed Price | EasyGo"
NEW_DESC = (
    "Brisbane airport transfer & Brisbane airport shuttle. "
    "Private 8-13 seater for CBD & Northern suburbs. "
    "Fixed prices, no hidden fees. 24/7."
)

OLD_TITLE = "Brisbane Airport Transfers & Shuttle | Fixed Price & Private (8-13 Seater) | EasyGo"
OLD_DESC = (
    "Reliable Brisbane airport transfers with fixed prices. "
    "EasyGo Airport Shuttle covers all Brisbane suburbs — book online in minutes, no hidden fees."
)


def update_brisbane_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    Region.objects.filter(slug="brisbane").update(
        meta_title=NEW_TITLE,
        meta_description=NEW_DESC,
    )


def reverse_brisbane_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    Region.objects.filter(slug="brisbane").update(
        meta_title=OLD_TITLE,
        meta_description=OLD_DESC,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0045_update_melbourne_seo"),
    ]

    operations = [
        migrations.RunPython(update_brisbane_seo, reverse_brisbane_seo),
    ]
