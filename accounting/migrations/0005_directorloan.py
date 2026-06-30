from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_transaction_excluded_transaction_needs_review'),
    ]

    operations = [
        migrations.CreateModel(
            name='DirectorLoan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('direction', models.CharField(
                    choices=[
                        ('contribution', 'Contribution (Director → Company)'),
                        ('repayment', 'Repayment (Company → Director)'),
                    ],
                    max_length=20,
                )),
                ('description', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'verbose_name': "Director's Loan",
                'verbose_name_plural': "Director's Loans",
                'ordering': ['date', 'pk'],
            },
        ),
    ]
