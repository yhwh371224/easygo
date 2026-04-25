from django.db import migrations


def update_melbourne_phone(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    Region.objects.filter(slug='melbourne').update(
        phone='+61406883355',
        phone_display='0406 883 355',
    )


def revert_melbourne_phone(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    Region.objects.filter(slug='melbourne').update(
        phone='03 9999 9999',
        phone_display='03 9999 9999',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0003_region_fields_and_suburb'),
    ]

    operations = [
        migrations.RunPython(update_melbourne_phone, reverse_code=revert_melbourne_phone),
    ]
