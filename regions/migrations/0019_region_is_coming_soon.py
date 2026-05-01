from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0018_requestlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='region',
            name='is_coming_soon',
            field=models.BooleanField(default=False),
        ),
    ]
