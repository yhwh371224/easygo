from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0043_populate_all_suburb_distance_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='terminalpickuppoint',
            name='is_default_point',
            field=models.BooleanField(default=False, help_text='드라이버 하루 첫 번째 미지정 픽업에 자동 배정 (Public 등)'),
        ),
        migrations.AddField(
            model_name='terminalpickuppoint',
            name='is_default_second',
            field=models.BooleanField(default=False, help_text='드라이버 하루 두 번째 이상 미지정 픽업에 자동 배정 (Rideshare 등)'),
        ),
    ]
