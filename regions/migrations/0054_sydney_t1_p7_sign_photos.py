from django.db import migrations

# Sydney T1 International: once customers reach P7 they need the next sign —
# "Public Pick-up →" or "← Rideshare". Swap the Step 4 photos for shots of
# those signs and point the last instruction line at them. The Accessible
# Pick-up photo is replaced with a smaller copy (the old one was too heavy
# for the arrival email).

S3 = 'https://easygo.s3.ap-southeast-2.amazonaws.com/'

POINTS = {
    'Public Pickup': {
        'last_line': '• At P7, follow the “Public Pick-up” signs (Step 4 photo) to meet your driver.',
        'old_last_line': '• At P7, follow the signs for “Public Pick-up” to meet your driver.',
        'photo_url': S3 + 'sydney-intl-public.webp',
        'old_photo_url': S3 + 'publicphoto.webp',
        'photo_title': 'Step 4 — At P7, follow “Public Pick-up”',
        'old_photo_title': 'Step 4 — Public Pick-up',
    },
    'Rideshare Pickup': {
        'last_line': '• At P7, follow the “Rideshare” signs (Step 4 photo) to meet your driver.',
        'old_last_line': '• At P7, follow the signs for “Rideshare” to meet your driver.',
        'photo_url': S3 + 'sydney-intl-rideshare.webp',
        'old_photo_url': S3 + 'ridesharephoto.webp',
        'photo_title': 'Step 4 — At P7, follow “Rideshare”',
        'old_photo_title': 'Step 4 — Rideshare',
    },
    'Accessible Pickup': {
        'photo_url': S3 + 'sydney-intl-accessible.webp',
        'old_photo_url': S3 + 'accessible_intl.webp',
        'photo_title': 'Accessible Pick-up sign',
        'old_photo_title': 'Accessbile Pickup image',
    },
}


def _points(apps):
    TerminalPickupPoint = apps.get_model('regions', 'TerminalPickupPoint')
    return TerminalPickupPoint.objects.filter(
        terminal__airport__code='SYD',
        terminal__name='T1 International',
        name__in=POINTS,
    )


def _apply(apps, direction):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    new, old = ('', 'old_') if direction == 'forwards' else ('old_', '')
    for point in _points(apps):
        spec = POINTS[point.name]
        if 'last_line' in spec:
            point.instruction = point.instruction.replace(
                spec[old + 'last_line'], spec[new + 'last_line'],
            )
            point.save(update_fields=['instruction'])
        PickupPointMap.objects.filter(
            pickup_point=point, url=spec[old + 'photo_url'],
        ).update(url=spec[new + 'photo_url'], title=spec[new + 'photo_title'])


def forwards(apps, schema_editor):
    _apply(apps, 'forwards')


def backwards(apps, schema_editor):
    _apply(apps, 'backwards')


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0053_sydney_t1_pickup_sign_photos'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
