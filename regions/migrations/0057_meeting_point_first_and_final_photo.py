from django.db import migrations

# Arrival emails: say where the meeting point is before the walking directions,
# so customers know the destination up front. Also drop the "P7 name only
# appears..." aside, and end the Sydney T1 Public Pick-up photos with a shot of
# the final pick-up area. Maps are ordered by (type, title), so the "Step 5"
# title puts it after Step 4.

S3 = 'https://easygo.s3.ap-southeast-2.amazonaws.com/'

ASIDE = ' The P7 name only appears once you get there — until then, just follow “Rideshare & Pick-up”.'

FIRST_LINES = {
    ('T1 International', 'Public Pickup'): '📍 Meeting point: “Public Pick-up” area.',
    ('T1 International', 'Rideshare Pickup'): '📍 Meeting point: “Rideshare” area.',
    ('T2 Domestic', 'Express Pick-up'): '📍 Meeting point: yellow “Express Pick-up waiting area” inside the P3 car park.',
}

PUBLIC_LAST_LINE = '• At P7, follow the “Public Pick-up” signs (Step 4 photo) to the Public Pick-up area (Step 5 photo) — your driver will meet you here.'
OLD_PUBLIC_LAST_LINE = '• At P7, follow the “Public Pick-up” signs (Step 4 photo) to meet your driver.'

FINAL_PHOTO_URL = S3 + 'sydney-airport-public-pickup-area.webp'
FINAL_PHOTO_TITLE = 'Step 5 — Final meeting point: Public Pick-up area'


def _point(apps, terminal, name):
    TerminalPickupPoint = apps.get_model('regions', 'TerminalPickupPoint')
    return TerminalPickupPoint.objects.filter(
        terminal__airport__code='SYD',
        terminal__name=terminal,
        name=name,
    ).first()


def forwards(apps, schema_editor):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    for (terminal, name), first_line in FIRST_LINES.items():
        point = _point(apps, terminal, name)
        if point is None:
            continue
        text = point.instruction.replace(ASIDE, '')
        if name == 'Public Pickup':
            text = text.replace(OLD_PUBLIC_LAST_LINE, PUBLIC_LAST_LINE)
            PickupPointMap.objects.update_or_create(
                pickup_point=point, url=FINAL_PHOTO_URL,
                defaults={'type': 'image', 'title': FINAL_PHOTO_TITLE},
            )
        point.instruction = f'{first_line}\n{text}'
        point.save(update_fields=['instruction'])


def backwards(apps, schema_editor):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    for (terminal, name), first_line in FIRST_LINES.items():
        point = _point(apps, terminal, name)
        if point is None:
            continue
        text = point.instruction.removeprefix(f'{first_line}\n')
        if terminal == 'T1 International':
            text = text.replace(
                '(Step 3 photo).',
                '(Step 3 photo).' + ASIDE,
            )
        if name == 'Public Pickup':
            text = text.replace(PUBLIC_LAST_LINE, OLD_PUBLIC_LAST_LINE)
            PickupPointMap.objects.filter(pickup_point=point, url=FINAL_PHOTO_URL).delete()
        point.instruction = text
        point.save(update_fields=['instruction'])


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0056_sydney_t2_express_photo_urls'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
