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
from blog.bird_proxy import send_bird_sms, _format_e164

logger = logging.getLogger(__name__)


def _get_active_mapping(from_number):
    return (
        PhoneMapping.objects
        .filter(from_number=from_number)
        .filter(expires_at__gt=timezone.now())
        .first()
    )


def _get_driver_target(driver_phone):
    """드라이버 번호로 현재 시간과 가장 가까운 활성 트립의 손님 번호 반환.

    드라이버 → 손님 PhoneMapping 은 저장하지 않으므로
    Post 모델에서 직접 조회: pickup_datetime + 4시간이 현재 이후인 트립 중
    pickup_time 기준으로 가장 가까운 트립 선택.
    """
    from blog.models import Post

    now = timezone.now()
    today = now.date()

    posts = (
        Post.objects
        .filter(
            driver__driver_contact=driver_phone,
            pickup_date=today,
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
                f'{post.pickup_date} {post.pickup_time or "00:00"}', '%Y-%m-%d %H:%M'
            )
            pickup_dt = timezone.make_aware(pickup_naive)
        except Exception:
            continue
        if pickup_dt + timedelta(hours=4) > now:
            active.append((pickup_dt, post))

    if not active:
        return None

    active.sort(key=lambda x: abs((x[0] - now).total_seconds()))
    _, closest = active[0]
    customer_phone = _format_e164(closest.contact)
    logger.debug('[Bird] Driver %s → closest trip Post %s → customer %s', driver_phone, closest.id, customer_phone)
    return customer_phone


@csrf_exempt
@require_POST
def sms_webhook(request):
    """Bird 인바운드 SMS 수신 → 매핑된 상대방에게 포워딩."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.error('[Bird SMS] Invalid JSON payload')
        return JsonResponse({'error': 'invalid json'}, status=400)

    try:
        msg = data.get('payload', {})
        from_number = msg.get('sender', {}).get('contact', {}).get('identifierValue')
        message_text = msg.get('body', {}).get('text', {}).get('text', '')
    except (AttributeError, KeyError) as e:
        logger.error('[Bird SMS] Payload parse error: %s', e)
        return JsonResponse({'error': 'payload parse error'}, status=400)

    if not from_number:
        logger.warning('[Bird SMS] No from_number in payload')
        return JsonResponse({'status': 'no from_number'})

    mapping = _get_active_mapping(from_number)
    if mapping:
        to_number = mapping.to_number
    else:
        to_number = _get_driver_target(from_number)

    if not to_number:
        logger.info('[Bird SMS] No active mapping or driver trip for %s', from_number)
        return JsonResponse({'status': 'no mapping'})

    try:
        send_bird_sms(to_number, message_text)
        logger.info('[Bird SMS] Forwarded %s → %s', from_number, to_number)
    except Exception as e:
        logger.error('[Bird SMS] Send failed: %s', e)
        return JsonResponse({'error': 'send failed'}, status=500)

    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_POST
def voice_webhook(request):
    """Bird voice.inbound 웹훅 → Bridge API로 발신자별 번호 포워딩."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.error('[Bird Voice] Invalid JSON payload')
        return JsonResponse({'error': 'invalid json'}, status=400)

    event_payload = data.get('payload', {})
    call_id = event_payload.get('id')
    from_number = event_payload.get('from')
    status = event_payload.get('status')

    if not call_id or not from_number:
        logger.warning('[Bird Voice] Missing callId or from: %s', data)
        return JsonResponse({'error': 'missing callId or from'}, status=400)

    logger.debug('[Bird Voice] Incoming call: from=%s callId=%s status=%s', from_number, call_id, status)

    if status != 'starting':
        logger.debug('[Bird Voice] Ignoring status=%s for callId=%s', status, call_id)
        return JsonResponse({'status': 'ignored'})

    mapping = _get_active_mapping(from_number)
    if mapping:
        destination = mapping.to_number
    else:
        destination = _get_driver_target(from_number)

    if not destination:
        logger.info('[Bird Voice] No active mapping or driver trip for %s', from_number)
        return JsonResponse({'status': 'no mapping'})

    workspace_id = settings.BIRD_WORKSPACE_ID
    channel_id = settings.BIRD_VOICE_CHANNEL_ID
    api_key = settings.BIRD_API_KEY
    bird_number = settings.BIRD_NUMBER

    url = (
        f'https://api.bird.com/workspaces/{workspace_id}'
        f'/channels/{channel_id}/calls/{call_id}/bridge'
    )
    payload = {
        'to': destination,
        'from': bird_number,
        'ringTimeout': 30,
        'hangupAfterBridge': True,
    }
    headers = {
        'Authorization': f'AccessKey {api_key}',
        'Content-Type': 'application/json',
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info('[Bird Voice] Bridged %s → %s (callId=%s)', from_number, destination, call_id)
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 400:
            logger.warning('[Bird Voice] Bridge 400 (call already ended) callId=%s: %s', call_id, e)
            return JsonResponse({'status': 'ok'})
        logger.error('[Bird Voice] Bridge API failed: %s', e)
        return JsonResponse({'error': 'bridge failed'}, status=500)
    except requests.RequestException as e:
        logger.error('[Bird Voice] Bridge API failed: %s', e)
        return JsonResponse({'error': 'bridge failed'}, status=500)

    return JsonResponse({'status': 'ok'})
