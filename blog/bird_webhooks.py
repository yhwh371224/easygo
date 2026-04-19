import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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
        sender_contacts = data.get('sender', {}).get('contacts', [])
        from_number = sender_contacts[0].get('identifierValue') if sender_contacts else None
        message_text = (
            data.get('body', {}).get('text', {}).get('text', '')
            or data.get('message', {}).get('text', '')
        )
    except (IndexError, AttributeError, KeyError) as e:
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
@require_POST
def voice_webhook(request):
    """Bird 인바운드 전화 수신 → 매핑된 상대방에게 연결."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    from_number = (
        data.get('from')
        or data.get('caller')
        or data.get('source', {}).get('number')
    )

    if not from_number:
        logger.warning('[Bird Voice] No from_number in payload')
        ncco = [{'action': 'talk', 'text': 'We could not connect your call. Please try again.'}]
        return JsonResponse(ncco, safe=False)

    mapping = _get_active_mapping(from_number)
    if not mapping:
        logger.info('[Bird Voice] No active mapping for %s', from_number)
        ncco = [{'action': 'talk', 'text': 'No active connection found for this number.'}]
        return JsonResponse(ncco, safe=False)

    logger.info('[Bird Voice] Connecting %s → %s', from_number, mapping.to_number)
    ncco = [
        {
            'action': 'connect',
            'from': settings.BIRD_NUMBER,
            'endpoint': [{'type': 'phone', 'number': mapping.to_number}],
        }
    ]
    return JsonResponse(ncco, safe=False)
