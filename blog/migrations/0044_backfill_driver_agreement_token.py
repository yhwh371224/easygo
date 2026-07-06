import secrets

from django.db import migrations


def backfill_agreement_token(apps, schema_editor):
    Driver = apps.get_model('blog', 'Driver')
    for driver in Driver.objects.filter(agreement_token__isnull=True):
        driver.agreement_token = secrets.token_urlsafe(32)
        driver.save(update_fields=['agreement_token'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0043_driver_agreement_token'),
    ]

    operations = [
        migrations.RunPython(backfill_agreement_token, noop),
    ]
