from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0035_driver_business_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='payment_match_digits',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='driver',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
