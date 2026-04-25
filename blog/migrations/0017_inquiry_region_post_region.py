from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0016_alter_driversettlement_settled_at'),
        ('regions', '0003_region_fields_and_suburb'),
    ]

    operations = [
        migrations.AddField(
            model_name='inquiry',
            name='region',
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='inquiries',
                to='regions.region',
            ),
        ),
        migrations.AddField(
            model_name='post',
            name='region',
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='posts',
                to='regions.region',
            ),
        ),
    ]
