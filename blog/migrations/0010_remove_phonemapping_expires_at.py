from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0009_add_use_proxy_to_post'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='phonemapping',
            name='expires_at',
        ),
    ]
