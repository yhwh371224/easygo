from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0033_driver_commission_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='commission_rate',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='이 부킹에 적용된 커미션 %. 드라이버 배정 시 기본값 자동 적용.',
                max_digits=4,
            ),
        ),
    ]
