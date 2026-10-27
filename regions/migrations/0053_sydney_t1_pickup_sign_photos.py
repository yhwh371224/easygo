from django.db import migrations

# Sydney T1 International: on site the P7 name only shows once you reach the
# car park — before that the signs just say "Rideshare & Pick-up", and there is
# no "P9" sign at all. Rewrite the Public / Rideshare directions around those
# signs and attach photos of them as Step 1–3. Maps are ordered by
# (type, title), so the "Step N" titles keep the photos in walking order.

S3 = 'https://easygo.s3.ap-southeast-2.amazonaws.com/'

STEP_PHOTOS = [
    ('Step 1 — “Rideshare & Pick-up” sign in the Arrivals Hall', S3 + 'sydney-intl-pickup-point-01.webp'),
    ('Step 2 — Keep following “Rideshare & Pick-up” outside', S3 + 'sydney-intl-pickup-point-02.webp'),
    ('Step 3 — P7 parking building', S3 + 'sydney-intl-pickup-point-03.webp'),
]

POINTS = {
    'Public Pickup': {
        'instruction': (
            '• After collecting your luggage, call or message your EasyGo driver.\n'
            '• Exit the Arrivals Hall and follow the “Rideshare & Pick-up” signs (see the Step 1 and Step 2 photos below).\n'
            '• The signs lead you to the P7 parking building (Step 3 photo). The P7 name only appears once you get there — until then, just follow “Rideshare & Pick-up”.\n'
            '• At P7, follow the signs for “Public Pick-up” to meet your driver.'
        ),
        'old_instruction': (
            '• After clearing customs and exiting the Arrivals Hall, follow the signs for “Rideshare & Pickup.”\n'
            '• Continue to the P7 parking building, then follow the signs for “Public Pickup"'
        ),
        'photo_url': S3 + 'publicphoto.webp',
        'photo_title': 'Step 4 — Public Pick-up',
        'old_photo_title': 'Public Pickup - image',
    },
    'Rideshare Pickup': {
        'instruction': (
            '• After collecting your luggage, call or message your EasyGo driver.\n'
            '• Exit the Arrivals Hall and follow the “Rideshare & Pick-up” signs (see the Step 1 and Step 2 photos below).\n'
            '• The signs lead you to the P7 parking building (Step 3 photo). The P7 name only appears once you get there — until then, just follow “Rideshare & Pick-up”.\n'
            '• At P7, follow the signs for “Rideshare” to meet your driver.'
        ),
        'old_instruction': (
            '• After clearing customs and exiting the Arrivals Hall, follow the signs for “Rideshare & Pickup.”\n'
            '• Continue to the P7 parking building, then follow the signs for “Rideshare.”'
        ),
        'photo_url': S3 + 'ridesharephoto.webp',
        'photo_title': 'Step 4 — Rideshare',
        'old_photo_title': 'T1 Rideshare Pickup - Image',
    },
}


def _points(apps):
    TerminalPickupPoint = apps.get_model('regions', 'TerminalPickupPoint')
    return TerminalPickupPoint.objects.filter(
        terminal__airport__code='SYD',
        terminal__name='T1 International',
        name__in=POINTS,
    )


def forwards(apps, schema_editor):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    for point in _points(apps):
        spec = POINTS[point.name]
        point.instruction = spec['instruction']
        point.save(update_fields=['instruction'])
        for title, url in STEP_PHOTOS:
            PickupPointMap.objects.update_or_create(
                pickup_point=point, url=url,
                defaults={'type': 'image', 'title': title},
            )
        PickupPointMap.objects.filter(
            pickup_point=point, url=spec['photo_url'],
        ).update(title=spec['photo_title'])


def backwards(apps, schema_editor):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    for point in _points(apps):
        spec = POINTS[point.name]
        point.instruction = spec['old_instruction']
        point.save(update_fields=['instruction'])
        PickupPointMap.objects.filter(
            pickup_point=point, url__in=[url for _, url in STEP_PHOTOS],
        ).delete()
        PickupPointMap.objects.filter(
            pickup_point=point, url=spec['photo_url'],
        ).update(title=spec['old_photo_title'])


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0052_pricingrule_short_trip_base_fee'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
