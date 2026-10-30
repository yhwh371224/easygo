from django.db import migrations

# Sydney T2 Domestic Express Pick-up: Step 1 and 2 photos were uploaded to S3
# under different names than 0055 assumed ("t2-express-pickup-o2" really has a
# letter o). Point the maps at the real files, and make the directions say
# plainly to follow the photos in order — Step 4 is where the driver meets you.
# Express Pick-up is inside P3, which comes after P2 (0055 wrongly moved it to
# P2): customers pass Priority Pick-up, then P2, and carry on to P3.

S3 = 'https://easygo.s3.ap-southeast-2.amazonaws.com/'

URLS = [
    (S3 + 'sydney-t2-express-01.webp', S3 + 't2-express-pickup-01.webp'),
    (S3 + 'sydney-t2-express-02.webp', S3 + 't2-express-pickup-o2.webp'),
]

INSTRUCTION = (
    '• After collecting your luggage, call or message your EasyGo driver.\n'
    '• Then follow the photos below in order, from Step 1 to Step 4 — each one shows the sign to look for next.\n'
    '• Step 1: from the baggage claim area, follow the “Priority & Express Pick-up” signs.\n'
    '• Step 2: outside, keep following “Priority & Express Pick-up” along the covered walkway.\n'
    '• Step 3: you will pass Priority Pick-up first — keep going and follow the “Express Pick-up” signs past the P2 car park.\n'
    '• Step 4: carry on to the P3 car park — this is the final meeting point. Wait in the yellow “Express Pick-up waiting area” inside P3 and your driver will meet you here.'
)

OLD_INSTRUCTION = (
    '• After collecting your luggage, call or message your EasyGo driver.\n'
    '• From the baggage claim area, follow the “Priority & Express Pick-up” signs (Step 1 photo).\n'
    '• Outside, keep following “Priority & Express Pick-up” along the covered walkway (Step 2 photo).\n'
    '• You will pass Priority Pick-up first — keep going and follow the “Express Pick-up” signs into the P2 car park (Step 3 photo).\n'
    '• Wait in the yellow “Express Pick-up waiting area” (Step 4 photo) to meet your driver.'
)

STEP3 = S3 + 'sydney-t2-express-03.webp'
STEP3_TITLE = 'Step 3 — Past Priority Pick-up, follow “Express Pick-up” past P2'
OLD_STEP3_TITLE = 'Step 3 — Past Priority Pick-up, follow “Express Pick-up” to P2'

STEP4 = S3 + 'sydney-t2-express-04.webp'
STEP4_TITLE = 'Step 4 — Final meeting point: Express Pick-up waiting area in P3'
OLD_STEP4_TITLE = 'Step 4 — Express Pick-up waiting area'


def _points(apps):
    TerminalPickupPoint = apps.get_model('regions', 'TerminalPickupPoint')
    return TerminalPickupPoint.objects.filter(
        terminal__airport__code='SYD',
        terminal__name='T2 Domestic',
        name='Express Pick-up',
    )


def _apply(apps, forwards):
    PickupPointMap = apps.get_model('regions', 'PickupPointMap')
    for point in _points(apps):
        point.instruction = INSTRUCTION if forwards else OLD_INSTRUCTION
        point.save(update_fields=['instruction'])
        for old_url, new_url in URLS:
            src, dst = (old_url, new_url) if forwards else (new_url, old_url)
            PickupPointMap.objects.filter(pickup_point=point, url=src).update(url=dst)
        PickupPointMap.objects.filter(pickup_point=point, url=STEP3).update(
            title=STEP3_TITLE if forwards else OLD_STEP3_TITLE,
        )
        PickupPointMap.objects.filter(pickup_point=point, url=STEP4).update(
            title=STEP4_TITLE if forwards else OLD_STEP4_TITLE,
        )


def forwards(apps, schema_editor):
    _apply(apps, True)


def backwards(apps, schema_editor):
    _apply(apps, False)


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0055_sydney_t2_express_sign_photos'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
