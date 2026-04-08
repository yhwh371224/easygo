from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('easygo_review', '0002_alter_post_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='reply',
            field=models.TextField(blank=True, null=True),
        ),
    ]
