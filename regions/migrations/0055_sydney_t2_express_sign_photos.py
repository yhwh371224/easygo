from django.db import migrations

# Sydney T2 Domestic Express Pick-up: the signs say "Priority & Express
# Pick-up" all the way out, you pass Priority Pick-up first, and the Express
# waiting area is in the P2 car park (the old text said P3). Rewrite the
# directions around those signs and attach photos of them as Step 1–4. Maps are
# ordered by (type, title), so the "Step N" titles keep the photos in walking
# order, ahead of the existing location map.

S3 = 'https://easygo.s3.ap-southeast-2.amazonaws.com/'

STEP_PHOTOS = [
    ('Step 1 — “Priority & Express Pick-up” sign at baggage claim', S3 + 'sydney-t2-express-01.webp'),
    ('Step 2 — Keep following “Priority & Express Pick-up” outside', S3 + 'sydney-t2-express-02.webp'),
    ('Step 3 — Past Priority Pick-up, follow “Express Pick-up” to P2', S3 + 'sydney-t2-express-03.webp'),
    ('Step 4 — Express Pick-up waiting area', S3 + 'sydney-t2-express-04.webp'),
]

INSTRUCTION = (
    '• After collecting your luggage, call or message your EasyGo driver.\n'
    '• From the baggage claim area, follow the “Priority & Express Pick-up” signs (Step 1 photo).\n'
    '• Outside, keep following “Priority & Express Pick-up” along the covered walkway (Step 2 photo).\n'
    '• You will pass Priority Pick-up first — keep going and follow the “Express Pick-up” signs into the P2 car park (Step 3 photo).\n'
    '• Wait in the yellow “Express Pick-up waiting area” (Step 4 photo) to meet your driver.'
)

OLD_INSTRUCTION = (
    '• After exiting the baggage claim area, follow the signs for “Express Pickup”.\n'
    '• Express Pickup is located in Parking Building P3.'
)


def _points(apps):
    TerminalPickupPoint = apps.get_model('regions', 'TerminalPickupPoint')
    return TerminalPickupPoint.objects.filter(
        terminal__airport__code='SYD',
        terminal__name='T2 Domestic',
        name='Express Pick-up',
    )


def forwards(apps, schema_editor):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    for point in _points(apps):
        point.instruction = INSTRUCTION
        point.save(update_fields=['instruction'])
        for title, url in STEP_PHOTOS:
            PickupPointMap.objects.update_or_create(
                pickup_point=point, url=url,
                defaults={'type': 'image', 'title': title},
            )


def backwards(apps, schema_editor):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    for point in _points(apps):
        point.instruction = OLD_INSTRUCTION
        point.save(update_fields=['instruction'])
        PickupPointMap.objects.filter(
            pickup_point=point, url__in=[url for _, url in STEP_PHOTOS],
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0054_sydney_t1_p7_sign_photos'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
