"""SearchSurveyResponse 를 blog 에서 easygo_review 로 옮긴다 (2/2 중 blog 쪽).

상태에서만 지운다 — 테이블은 easygo_review 가 이어받았으므로 DROP 하면 안 된다.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0080_searchsurveyresponse_discount_amount_and_more'),
        ('easygo_review', '0004_move_searchsurveyresponse_from_blog'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='SearchSurveyResponse'),
            ],
        ),
    ]
