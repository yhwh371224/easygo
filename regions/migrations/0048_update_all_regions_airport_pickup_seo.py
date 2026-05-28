from django.db import migrations

SEO_DATA = {
    "sydney": {
        "new_title": "Sydney Airport Pickup & Transfer | Fixed Price | EasyGo",
        "new_desc": (
            "Sydney airport pickup & transfer — private 8-13 seater with flight tracking. "
            "Fixed price for all Sydney suburbs. Airport shuttle for families & groups. 24/7."
        ),
        "old_title": None,
        "old_desc": None,
    },
    "brisbane": {
        "new_title": "Brisbane Airport Pickup & Transfer | Fixed Price | EasyGo",
        "new_desc": (
            "Brisbane airport pickup from BNE — private 8-13 seater airport shuttle. "
            "CBD, Northside & Logan. No toll surprises, fixed prices, no hidden fees. 24/7."
        ),
        "old_title": "Brisbane Airport Transfer & Shuttle | Fixed Price | EasyGo",
        "old_desc": (
            "Brisbane airport transfer & Brisbane airport shuttle. "
            "Private 8-13 seater for CBD & Northern suburbs. "
            "Fixed prices, no hidden fees. 24/7."
        ),
    },
    "melbourne": {
        "new_title": "Melbourne Airport Pickup & Transfer | Fixed Price | EasyGo",
        "new_desc": (
            "Melbourne airport pickup from Tullamarine (MEL). "
            "Private 8-13 seater airport shuttle — CityLink included, all 4 terminals covered. "
            "Fixed prices. 24/7."
        ),
        "old_title": "Melbourne Airport Transfer & Shuttle | Fixed Price | EasyGo",
        "old_desc": (
            "Melbourne airport transfer & Melbourne airport shuttle. "
            "Private 8-13 seater for CBD, Northern & Western suburbs. "
            "Fixed prices, no hidden fees. 24/7."
        ),
    },
    "gold-coast": {
        "new_title": "Gold Coast Airport Pickup & Transfer | Fixed Price | EasyGo",
        "new_desc": (
            "Gold Coast airport pickup from OOL Coolangatta. "
            "Private 8-13 seater airport shuttle — surfboards welcome, NSW border service. "
            "Fixed prices. 24/7."
        ),
        "old_title": "Gold Coast Airport Transfer & Shuttle | Fixed Price | EasyGo",
        "old_desc": (
            "Gold Coast airport transfer & Gold Coast airport shuttle. "
            "Private 8-13 seater for Gold Coast suburbs. "
            "Fixed prices, no hidden fees. 24/7."
        ),
    },
}


def update_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    for slug, data in SEO_DATA.items():
        Region.objects.filter(slug=slug).update(
            meta_title=data["new_title"],
            meta_description=data["new_desc"],
        )


def reverse_seo(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    for slug, data in SEO_DATA.items():
        Region.objects.filter(slug=slug).update(
            meta_title=data["old_title"],
            meta_description=data["old_desc"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0047_update_gold_coast_seo"),
    ]

    operations = [
        migrations.RunPython(update_seo, reverse_seo),
    ]
