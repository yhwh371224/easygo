from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0026_rename_post_fuel_surcharge_to_surcharge'),
    ]

    operations = [
        migrations.RenameField(
            model_name='inquiry',
            old_name='fuel_surcharge',
            new_name='surcharge',
        ),
    ]
