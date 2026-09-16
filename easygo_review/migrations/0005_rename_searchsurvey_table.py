"""이사 마무리: 테이블 이름을 새 앱 기준으로 바꾼다.

blog_searchsurveyresponse → easygo_review_searchsurveyresponse.
ALTER TABLE RENAME 한 방이라 데이터는 그대로 따라온다.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('easygo_review', '0004_move_searchsurveyresponse_from_blog'),
        ('blog', '0081_delete_searchsurveyresponse'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='searchsurveyresponse',
            table=None,
        ),
    ]
