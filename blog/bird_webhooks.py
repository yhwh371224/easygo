import json
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

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


def _say_step(text):
    """레거시 Bird Call Flows say 액션."""
    return {'action': 'say', 'options': {'payload': text, 'voice': 'male', 'language': 'en-AU'}}


@csrf_exempt
@require_GET
def voice_webhook(request):
    """Bird 인바운드 전화 수신 → 매핑된 상대방에게 연결.

    레거시 MessageBird/Bird Call Flows 방식:
    - Bird가 GET 요청으로 웹훅 호출 (query params: source=발신자, destination=착신번호)
    - 응답 JSON {"steps": [...]} 으로 콜 플로우 제어
    - 웹훅 URL은 Bird 대시보드 Phone Number 설정에서 등록 (SMS 웹훅 구독과 다름)

    신규 Bird API는 Flows + REST API 방식으로 변경됐으나
    레거시 방식이 여전히 동작하는 동안 이 방식을 유지.
    """
    from_number = request.GET.get('source') or request.GET.get('from')
    destination = request.GET.get('destination') or request.GET.get('to')
    logger.debug('[Bird Voice] Incoming call: source=%s destination=%s params=%s',
                 from_number, destination, dict(request.GET))

    if not from_number:
        logger.warning('[Bird Voice] No from_number in query params: %s', dict(request.GET))
        return JsonResponse({'steps': [_say_step('We could not connect your call. Please try again.')]})

    mapping = _get_active_mapping(from_number)
    if mapping:
        to_number = mapping.to_number
    else:
        to_number = _get_driver_target(from_number)

    if not to_number:
        logger.info('[Bird Voice] No active mapping or driver trip for %s', from_number)
        return JsonResponse({'steps': [_say_step('No active connection found for this number.')]})

    logger.info('[Bird Voice] Connecting %s → %s', from_number, to_number)
    return JsonResponse({
        'steps': [
            {'action': 'transfer', 'options': {'destination': to_number}},
        ]
    })
