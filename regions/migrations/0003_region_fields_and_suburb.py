from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


def seed_sydney_update_melbourne(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')

    Region.objects.get_or_create(
        slug='sydney',
        defaults={
            'name': 'Sydney',
            'airport_code': 'SYD',
            'airport_name': 'Sydney Airport (SYD)',
            'timezone': 'Australia/Sydney',
            'phone': '+61406883355',
            'phone_display': '0406 883 355',
            'state_code': 'NSW',
            'address': 'Sydney, NSW',
            'latitude': Decimal('-33.8261'),
            'longitude': Decimal('151.2007'),
            'airport_lat': Decimal('-33.9399'),
            'airport_lng': Decimal('151.1753'),
            'meta_description': (
                'EasyGo Airport Shuttle provides private airport transfer across Sydney. '
                'Punctual, luggage-friendly service for individuals, families, and groups.'
            ),
            'is_active': True,
        },
    )

    Region.objects.filter(slug='melbourne').update(
        state_code='VIC',
        airport_name='Melbourne Airport (MEL)',
        airport_lat=Decimal('-37.6690'),
        airport_lng=Decimal('144.8410'),
        latitude=Decimal('-37.8136'),
        longitude=Decimal('144.9631'),
        address='Melbourne, VIC',
        phone_display='03 9999 9999',
    )


def unseed_sydney_revert_melbourne(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    Region.objects.filter(slug='sydney').delete()
    Region.objects.filter(slug='melbourne').update(
        state_code='',
        airport_name='',
        airport_lat=None,
        airport_lng=None,
        latitude=None,
        longitude=None,
        address='',
        phone_display='',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0002_seed_regions'),
    ]

    operations = [
        # --- New fields on Region ---
        migrations.AddField(
            model_name='region',
            name='state_code',
            field=models.CharField(blank=True, default='', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='region',
            name='airport_name',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='region',
            name='airport_lat',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='region',
            name='airport_lng',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='region',
            name='phone_display',
            field=models.CharField(blank=True, default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='region',
            name='meta_description',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='region',
            name='address',
            field=models.CharField(blank=True, default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='region',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='region',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
        # --- New RegionSuburb model ---
        migrations.CreateModel(
            name='RegionSuburb',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=6)),
                ('zone', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('meta_title', models.CharField(blank=True, max_length=60)),
                ('meta_description', models.CharField(blank=True, max_length=500)),
                ('region', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='suburbs',
                    to='regions.region',
                )),
            ],
            options={
                'ordering': ['zone', 'name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='regionsuburb',
            unique_together={('region', 'slug')},
        ),
        # --- Data: add Sydney, update Melbourne ---
        migrations.RunPython(
            seed_sydney_update_melbourne,
            reverse_code=unseed_sydney_revert_melbourne,
        ),
    ]
