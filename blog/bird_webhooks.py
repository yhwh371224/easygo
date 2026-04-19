import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from blog.models import PhoneMapping
from blog.bird_proxy import send_bird_sms

logger = logging.getLogger(__name__)


def _get_active_mapping(from_number):
    return (
        PhoneMapping.objects
        .filter(from_number=from_number)
        .filter(expires_at__gt=timezone.now())
        .first()
    )


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
    if not mapping:
        logger.info('[Bird SMS] No active mapping for %s', from_number)
        return JsonResponse({'status': 'no mapping'})

    try:
        send_bird_sms(mapping.to_number, message_text)
        logger.info('[Bird SMS] Forwarded %s → %s', from_number, mapping.to_number)
    except Exception as e:
        logger.error('[Bird SMS] Send failed: %s', e)
        return JsonResponse({'error': 'send failed'}, status=500)

    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_GET
def voice_webhook(request):
    """Bird 인바운드 전화 수신 → 매핑된 상대방에게 연결.

    Bird sends GET with query params: source (caller), destination (called number).
    Must respond with a call flow JSON: {"steps": [...]}
    """
    from_number = request.GET.get('source') or request.GET.get('from')

    if not from_number:
        logger.warning('[Bird Voice] No from_number in query params: %s', dict(request.GET))
        flow = {'steps': [{'action': 'say', 'options': {'payload': 'We could not connect your call. Please try again.'}}]}
        return JsonResponse(flow)

    mapping = _get_active_mapping(from_number)
    if not mapping:
        logger.info('[Bird Voice] No active mapping for %s', from_number)
        flow = {'steps': [{'action': 'say', 'options': {'payload': 'No active connection found for this number.'}}]}
        return JsonResponse(flow)

    logger.info('[Bird Voice] Connecting %s → %s', from_number, mapping.to_number)
    flow = {
        'steps': [
            {
                'action': 'transfer',
                'options': {'destination': mapping.to_number},
            }
        ]
    }
    return JsonResponse(flow)
