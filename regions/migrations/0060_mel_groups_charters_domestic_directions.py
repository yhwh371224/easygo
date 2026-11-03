from django.db import migrations

# Melbourne T2 Groups & Charters is now the meeting point for every arrival,
# domestic included — drop the customs wording and tell domestic guests to
# walk to T2 International.

NEW = (
    '1. After collecting your bags, walk out through the Arrivals Hall exit doors.\n'
    '• Domestic flights (T1 Qantas, T3 Virgin, T4 Jetstar/Rex): the meeting point is at '
    'T2 International. All terminals are connected and within walking distance — follow '
    'the signs to T2 International.\n'
    '2. Once outside T2, stay on the ground level. Look for the overhead signs that say '
    '"Groups & Charters".'
)

OLD = (
    '1. After you collect your bags and clear Customs, walk out through the Arrivals Hall exit doors.\r\n'
    '2. Once outside, stay on the ground level. Look for the overhead signs that say "Groups & Charters".'
)


def _points(apps):
    TerminalPickupPoint = apps.get_model('regions', 'TerminalPickupPoint')
    return TerminalPickupPoint.objects.filter(
        terminal__airport__code='MEL',
        terminal__name='T2 International',
        name='Groups & Charters',
    )


def forwards(apps, schema_editor):
    _points(apps).update(instruction=NEW)


def backwards(apps, schema_editor):
    _points(apps).update(instruction=OLD)


class Migration(migrations.Migration):
    dependencies = [
        ('regions', '0059_melbourne_arrivals_meet_at_t2_groups'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
