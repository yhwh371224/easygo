from django.db import migrations

# Melbourne: every arrival (international and domestic) meets at
# T2 International — Groups & Charters. Groups come out at T2, and the
# Groups & Charters pickup is right outside, so one spot for everyone.


def forwards(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    TerminalPickupPoint = apps.get_model('regions', 'TerminalPickupPoint')
    point = TerminalPickupPoint.objects.filter(
        terminal__airport__code='MEL',
        terminal__type='intl',
        terminal__name='T2 International',
        name='Groups & Charters',
    ).first()
    if point is None:  # 로컬/테스트 DB 에 데이터가 없으면 건너뛴다.
        return
    Region.objects.filter(slug='melbourne').update(arrival_meeting_point=point)


def backwards(apps, schema_editor):
    Region = apps.get_model('regions', 'Region')
    Region.objects.filter(slug='melbourne').update(arrival_meeting_point=None)


class Migration(migrations.Migration):
    dependencies = [
        ('regions', '0058_region_arrival_meeting_point'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
