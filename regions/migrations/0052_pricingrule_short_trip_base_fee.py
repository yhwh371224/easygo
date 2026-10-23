from decimal import Decimal

from django.db import migrations, models


def set_base_fee_20(apps, schema_editor):
    PricingRule = apps.get_model("regions", "PricingRule")
    PricingRule.objects.filter(base_fee=Decimal("30.00")).update(base_fee=Decimal("20.00"))


def set_base_fee_30(apps, schema_editor):
    PricingRule = apps.get_model("regions", "PricingRule")
    PricingRule.objects.filter(base_fee=Decimal("20.00")).update(base_fee=Decimal("30.00"))


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0051_pricingrule_base_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricingrule',
            name='short_trip_km',
            field=models.DecimalField(decimal_places=2, default=15.0, help_text='Suburbs closer than this use short_trip_base_fee instead of base_fee', max_digits=5),
        ),
        migrations.AddField(
            model_name='pricingrule',
            name='short_trip_base_fee',
            field=models.DecimalField(decimal_places=2, default=30.0, help_text='Flat amount added for suburbs under short_trip_km', max_digits=6),
        ),
        migrations.AlterField(
            model_name='pricingrule',
            name='base_fee',
            field=models.DecimalField(decimal_places=2, default=20.0, help_text='Flat amount added after distance × rate_per_km', max_digits=6),
        ),
        migrations.RunPython(set_base_fee_20, set_base_fee_30),
    ]
