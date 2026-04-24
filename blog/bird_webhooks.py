import json
import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from blog.models import PhoneMapping
from blog.bird_proxy import send_bird_sms

from blog.sms_utils import normalize_phone 

logger = logging.getLogger(__name__)


# =========================
# Mapping lookup (FIX #3: normalize key)
# =========================
def _get_active_mapping(from_number):
    from_number = normalize_phone(from_number)
    return PhoneMapping.objects.filter(from_number=from_number).first()


# ==========================================================
# DRIVER TARGET LOGIC (UNCHANGED except safety fix)
# ==========================================================
def _get_driver_target(driver_phone):
    from blog.models import Post

    now = timezone.now()
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    # ❗ FIX: driver is already +61 → DO NOT re-normalize again
    e164_driver = driver_phone

    posts = (
        Post.objects
        .filter(
            driver__driver_contact=e164_driver,
            pickup_date__in=[today, tomorrow],
            cancelled=False,
            use_proxy=True,
        )
        .exclude(contact__isnull=True)
        .exclude(contact='')
    )

    active = []
    for post in posts:
        try:
            pickup_naive = datetime.strptime(
                f'{post.pickup_date} {post.pickup_time or "00:00"}',
                '%Y-%m-%d %H:%M'
            )
            pickup_dt = timezone.make_aware(pickup_naive)
        except Exception:
            continue

        if pickup_dt + timedelta(hours=1) > now:
            active.append((pickup_dt, post))

    if not active:
        return None

    active.sort(key=lambda x: abs((x[0] - now).total_seconds()))
    _, closest = active[0]

    customer_phone = normalize_phone(closest.contact)

    logger.debug(
        '[Bird] Driver %s → Post %s → customer %s',
        driver_phone,
        closest.id,
        customer_phone
    )

    return customer_phone


# =========================
# SMS WEBHOOK
# =========================
@csrf_exempt
@require_POST
def sms_webhook(request):

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    logger.debug('[Bird SMS RAW] %s', json.dumps(data, indent=2))

    try:
        msg = data.get('payload', {})
        from_number = msg.get('sender', {}).get('contact', {}).get('identifierValue')
        message_text = msg.get('body', {}).get('text', {}).get('text', '')
    except Exception as e:
        logger.error('[Bird SMS] Payload parse error: %s', e)
        return JsonResponse({'error': 'payload parse error'}, status=400)

    if not from_number:
        return JsonResponse({'status': 'no from_number'})

    # ✔ normalize ONLY customer side
    from_number = normalize_phone(from_number)

    mapping = _get_active_mapping(from_number)

    if mapping:
        to_number = mapping.to_number
        route = "mapping"
    else:
        to_number = _get_driver_target(from_number)
        route = "post_fallback"

    if not to_number:
        return JsonResponse({'status': 'no mapping'})

    try:
        send_bird_sms(to_number, message_text)

        logger.info(
            '[Bird SMS] %s → %s via %s',
            from_number,
            to_number,
            route
        )

    except Exception as e:
        logger.error('[Bird SMS] Send failed: %s', e)
        return JsonResponse({'error': 'send failed'}, status=500)

    return JsonResponse({'status': 'ok'})


# =========================
# VOICE WEBHOOK
# =========================
@csrf_exempt
@require_POST
def voice_webhook(request):

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    event = data.get('payload', {})
    call_id = event.get('id')
    from_number = event.get('from')
    status = event.get('status')

    if not call_id or not from_number:
        return JsonResponse({'error': 'missing data'}, status=400)

    from_number = normalize_phone(from_number)

    # ✔ relaxed status handling
    if status not in ['starting', 'initiated']:
        return JsonResponse({'status': 'ignored'})

    mapping = _get_active_mapping(from_number)

    if mapping:
        destination = mapping.to_number
        route = "mapping"
    else:
        destination = _get_driver_target(from_number)
        route = "post_fallback"

    if not destination:
        return JsonResponse({'status': 'no mapping'})

    url = (
        f'https://api.bird.com/workspaces/{settings.BIRD_WORKSPACE_ID}'
        f'/channels/{settings.BIRD_VOICE_CHANNEL_ID}/calls/{call_id}/bridge'
    )

    payload = {
        'to': destination,
        'from': settings.BIRD_NUMBER,
        'ringTimeout': 30,
        'hangupAfterBridge': True,
    }

    headers = {
        'Authorization': f'AccessKey {settings.BIRD_API_KEY}',
        'Content-Type': 'application/json',
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()

        logger.info(
            '[Bird Voice] %s → %s via %s',
            from_number,
            destination,
            route
        )

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None

        if status_code == 400:
            return JsonResponse({'status': 'ok'})

        logger.error('[Bird Voice] HTTP error: %s', e)
        return JsonResponse({'error': 'bridge failed'}, status=500)

    except requests.RequestException as e:
        logger.error('[Bird Voice] Request error: %s', e)
        return JsonResponse({'error': 'bridge failed'}, status=500)

    return JsonResponse({'status': 'ok'})