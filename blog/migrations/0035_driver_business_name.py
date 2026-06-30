from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0034_post_commission_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='business_name',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
