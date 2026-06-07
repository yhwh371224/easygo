from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0029_driver_abn'),
    ]

    operations = [
        migrations.RenameField(
            model_name='inquiry',
            old_name='meeting_point',
            new_name='customer_history',
        ),
        migrations.RenameField(
            model_name='post',
            old_name='meeting_point',
            new_name='customer_history',
        ),
    ]
