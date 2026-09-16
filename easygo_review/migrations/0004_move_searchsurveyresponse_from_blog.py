"""SearchSurveyResponse 를 blog 에서 easygo_review 로 옮긴다 (1/2).

blog 쪽에 쌓인 게 너무 많아서 설문만 떼어냈다. 이 마이그레이션은 상태(state)만
옮기고 DB 는 건드리지 않는다 — 테이블은 아직 blog_searchsurveyresponse 그대로이고,
실제 rename 은 0005 에서 한다. 이렇게 쪼개야 기존 응답 데이터가 안 날아간다.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0080_searchsurveyresponse_discount_amount_and_more'),
        ('easygo_review', '0003_alter_post_is_published'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='SearchSurveyResponse',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                                   serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100)),
                        ('email', models.EmailField(max_length=254)),
                        ('keyword', models.CharField(max_length=200)),
                        ('page', models.CharField(max_length=50)),
                        ('landed', models.CharField(max_length=100)),
                        ('landed_note', models.CharField(blank=True, max_length=300)),
                        ('liked', models.TextField(blank=True)),
                        ('improve', models.TextField(blank=True)),
                        ('created', models.DateTimeField(auto_now_add=True)),
                        ('discount_amount', models.PositiveIntegerField(default=0, help_text='달러 정액 할인')),
                        ('discount_code', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                        ('discount_emailed', models.DateTimeField(blank=True, null=True)),
                        ('discount_expires', models.DateField(blank=True, null=True)),
                        ('discount_redeemed', models.DateTimeField(blank=True, null=True)),
                        ('discount_redeemed_note', models.CharField(blank=True, help_text='어느 예약에 썼는지 메모', max_length=200)),
                    ],
                    options={
                        'ordering': ['-created'],
                        'db_table': 'blog_searchsurveyresponse',
                    },
                ),
            ],
        ),
    ]
