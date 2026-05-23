from django.db import migrations

NEW_TITLE = "Gold Coast Airport Transfer & Shuttle | Fixed Price | EasyGo"
NEW_DESC = (
    "Gold Coast airport transfer & Gold Coast airport shuttle. "
    "Private 8-13 seater for Gold Coast suburbs. "
    "Fixed prices, no hidden fees. 24/7."
)

OLD_TITLE = "Gold Coast Airport Transfers & Shuttle | Fixed Price & Private (8-13 Seater) | EasyGo"
OLD_DESC = (
    "Affordable Gold Coast airport transfers with fixed prices. "
    "EasyGo Airport Shuttle serves all Gold Coast suburbs — easy online booking, no hidden fees."
)


def update_gold_coast_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    Region.objects.filter(slug="gold-coast").update(
        meta_title=NEW_TITLE,
        meta_description=NEW_DESC,
    )


def reverse_gold_coast_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    Region.objects.filter(slug="gold-coast").update(
        meta_title=OLD_TITLE,
        meta_description=OLD_DESC,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0046_update_brisbane_seo"),
    ]

    operations = [
        migrations.RunPython(update_gold_coast_seo, reverse_gold_coast_seo),
    ]
