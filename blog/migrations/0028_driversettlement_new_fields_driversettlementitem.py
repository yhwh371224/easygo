import datetime
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def backfill_settlement_numbers(apps, schema_editor):
    """Assign unique placeholder numbers to any legacy DriverSettlement rows."""
    DriverSettlement = apps.get_model('blog', 'DriverSettlement')
    for s in DriverSettlement.objects.all():
        s.settlement_number = f'LEGACY-{s.pk:06d}'
        s.save(update_fields=['settlement_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0027_rename_inquiry_fuel_surcharge_to_surcharge'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Drop old 'amount' field (replaced by the breakdown columns below).
        migrations.RemoveField(
            model_name='driversettlement',
            name='amount',
        ),

        # Add settlement_number as nullable first so existing rows survive,
        # then backfill, then enforce the unique non-null constraint.
        migrations.AddField(
            model_name='driversettlement',
            name='settlement_number',
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
        migrations.RunPython(backfill_settlement_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='driversettlement',
            name='settlement_number',
            field=models.CharField(db_index=True, max_length=60, unique=True),
        ),

        # Period dates — one-off sentinel for legacy rows; preserve_default=False
        # means this default is not stored in the schema after migration.
        migrations.AddField(
            model_name='driversettlement',
            name='from_date',
            field=models.DateField(default=datetime.date(2020, 1, 1)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='to_date',
            field=models.DateField(default=datetime.date(2020, 1, 1)),
            preserve_default=False,
        ),

        # Money breakdown fields (all have real defaults; no one-off needed).
        migrations.AddField(
            model_name='driversettlement',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='cash_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='paid_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='gst_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),

        # Status / workflow fields.
        migrations.AddField(
            model_name='driversettlement',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('locked', 'Locked'),
                    ('paid', 'Paid'),
                    ('exported', 'Exported'),
                ],
                default='draft',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='payment_method',
            field=models.CharField(
                choices=[('payid', 'PayID'), ('bank', 'Bank Transfer')],
                default='payid',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # Xero export tracking.
        migrations.AddField(
            model_name='driversettlement',
            name='xero_exported',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='xero_exported_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='xero_reference',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='driversettlement',
            name='xero_invoice_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),

        # Audit timestamp — auto_now_add; one-off default for existing rows.
        migrations.AddField(
            model_name='driversettlement',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),

        # settled_by gains blank=True to match the new model definition.
        migrations.AlterField(
            model_name='driversettlement',
            name='settled_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # New related model for line items.
        # Note: rcti_number is intentionally absent — it is a Python property
        # on DriverSettlement that returns settlement_number; no DB column.
        migrations.CreateModel(
            name='DriverSettlementItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('gst_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('line_total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('post', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to='blog.post',
                )),
                ('settlement', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='blog.driversettlement',
                )),
            ],
            options={
                'unique_together': {('settlement', 'post')},
            },
        ),
    ]
