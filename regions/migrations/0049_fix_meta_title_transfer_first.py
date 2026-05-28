from django.db import migrations

TITLES = {
    "sydney": (
        "Sydney Airport Transfer & Pickup | Fixed Price | EasyGo",
        "Sydney Airport Pickup & Transfer | Fixed Price | EasyGo",
    ),
    "brisbane": (
        "Brisbane Airport Transfer & Pickup | Fixed Price | EasyGo",
        "Brisbane Airport Pickup & Transfer | Fixed Price | EasyGo",
    ),
    "melbourne": (
        "Melbourne Airport Transfer & Pickup | Fixed Price | EasyGo",
        "Melbourne Airport Pickup & Transfer | Fixed Price | EasyGo",
    ),
    "gold-coast": (
        "Gold Coast Airport Transfer & Pickup | Fixed Price | EasyGo",
        "Gold Coast Airport Pickup & Transfer | Fixed Price | EasyGo",
    ),
}


def forward(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    for slug, (new, _) in TITLES.items():
        Region.objects.filter(slug=slug).update(meta_title=new)


def backward(apps, schema_editor):
    Region = apps.get_model("regions", "Region")
    for slug, (_, old) in TITLES.items():
        Region.objects.filter(slug=slug).update(meta_title=old)


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0048_update_all_regions_airport_pickup_seo"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
