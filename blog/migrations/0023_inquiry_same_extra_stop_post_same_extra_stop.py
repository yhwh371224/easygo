from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0022_post_extra_stop_post_special_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='inquiry',
            name='same_extra_stop',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='post',
            name='same_extra_stop',
            field=models.BooleanField(default=False),
        ),
    ]
