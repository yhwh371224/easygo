import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps

import requests
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from blog.models import PhoneMapping
from blog.bird_proxy import send_bird_sms

from blog.sms_utils import normalize_phone

logger = logging.getLogger('bird_webhooks')

# Bird retries a failed delivery for up to 8 hours, so the 10s tolerance in
# their sample would reject every retry. 5 minutes matches their own Standard
# Webhooks guidance.
SIGNATURE_TOLERANCE_SECONDS = 300


# =========================
# Signature verification
# =========================
def _signature_is_valid(request):
    """
    Check Bird's HMAC over "timestamp\\nURL\\nsha256(body)". Decides nothing —
    verify_bird_signature() below decides whether a failure is fatal.

    The URL is rebuilt from BIRD_WEBHOOK_BASE_URL rather than from the request,
    so it always matches the URL the subscription was registered with: both are
    built from that one setting. Reconstructing it from proxy headers instead
    would silently reject every webhook the day a header changed shape.
    """

    signature = request.headers.get('messagebird-signature')
    timestamp = request.headers.get('messagebird-request-timestamp')

    if not signature or not timestamp:
        logger.warning('[Bird] Webhook carries no signature path=%s', request.path)
        return False

    try:
        skew = abs(int(time.time()) - int(timestamp))
    except (TypeError, ValueError):
        logger.warning('[Bird] Bad timestamp header: %r', timestamp)
        return False

    if skew > SIGNATURE_TOLERANCE_SECONDS:
        logger.warning('[Bird] Stale webhook skew=%ss path=%s', skew, request.path)
        return False

    url = f'{settings.BIRD_WEBHOOK_BASE_URL}{request.path}'
    payload = b'\n'.join([
        timestamp.encode(),
        url.encode(),
        hashlib.sha256(request.body).digest(),
    ])
    expected = hmac.new(
        settings.BIRD_WEBHOOK_SIGNING_KEY.encode(), payload, hashlib.sha256,
    ).digest()

    try:
        provided = base64.b64decode(signature)
    except ValueError:
        logger.warning('[Bird] Undecodable signature path=%s', request.path)
        return False

    if not hmac.compare_digest(expected, provided):
        logger.warning('[Bird] Signature mismatch for url=%s', url)
        return False

    return True


def verify_bird_signature(view):
    """
    Reject unsigned/forged webhooks once BIRD_WEBHOOK_REQUIRE_SIGNATURE is on.

    Until then we check and log but still serve the request: the signature
    covers the URL, so a base-URL that doesn't match what Bird has registered
    would take every call and text down at once. Run in this mode long enough
    to see "[Bird] Signature ok" in the logs, then enforce.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not settings.BIRD_WEBHOOK_SIGNING_KEY:
            return view(request, *args, **kwargs)

        if _signature_is_valid(request):
            logger.debug('[Bird] Signature ok path=%s', request.path)
            return view(request, *args, **kwargs)

        if settings.BIRD_WEBHOOK_REQUIRE_SIGNATURE:
            return JsonResponse({'error': 'invalid signature'}, status=403)

        logger.warning(
            '[Bird] Signature check failed but not enforced path=%s — fix this '
            'before setting BIRD_WEBHOOK_REQUIRE_SIGNATURE=True',
            request.path,
        )
        return view(request, *args, **kwargs)

    return wrapper


# =========================
# Mapping lookup (FIX #3: normalize key)
# =========================
def _get_active_mapping(from_number):
    from_number = normalize_phone(from_number)
    return PhoneMapping.objects.filter(from_number=from_number).first()


# =========================
# Driver lookup by caller ID
# =========================
def _find_driver_by_contact(e164_phone):
    """
    Match an inbound caller ID to a Driver.

    driver_contact is free text — some rows are E.164, others local ('04...'),
    so filtering on it with the caller's normalized number silently misses and
    the driver's leg never bridges. Normalize both sides before comparing.
    """

    from blog.models import Driver

    if not e164_phone:
        return None

    driver = Driver.objects.filter(driver_contact=e164_phone).first()
    if driver:
        return driver

    candidates = (
        Driver.objects
        .exclude(driver_contact__isnull=True)
        .exclude(driver_contact='')
        .select_related('virtual_number')
    )
    for candidate in candidates:
        if normalize_phone(candidate.driver_contact) == e164_phone:
            return candidate

    return None


# ==========================================================
# DRIVER TARGET LOGIC
# ==========================================================
def _get_driver_target(driver_phone):
    from blog.models import Post

    now = timezone.now()
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    driver = _find_driver_by_contact(driver_phone)
    if not driver:
        return None

    posts = (
        Post.objects
        .filter(
            driver=driver,
            pickup_date__in=[today, tomorrow],
            cancelled=False,
            use_proxy=True,
        )
        .exclude(contact__isnull=True)
        .exclude(contact='')
        .select_related('driver__virtual_number')
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
# Route resolution
# =========================
def _resolve_route(from_number):
    """
    Who this caller/texter should reach. Returns (destination, route).

    Keyed on the caller, never on the number dialled: a customer reaches their
    driver and a driver reaches their closest customer, whichever of our
    numbers they rang.
    """

    mapping = _get_active_mapping(from_number)

    if mapping:
        return mapping.to_number, 'mapping'

    return _get_driver_target(from_number), 'post_fallback'


def _arriving_channel(channel_id, default_channel_id, request):
    """
    The Bird channel this webhook arrived on.

    Subscriptions we create carry the channel in the URL, which is the only
    thing that tells us which of our numbers was dialled — the event body is
    not documented to carry it. A bare URL means a subscription still points at
    the legacy path, which silently pins traffic to one number.
    """

    if channel_id:
        # The <uuid:...> converter hands us a UUID; channel ids are stored and
        # sent to Bird as strings.
        return str(channel_id)

    logger.warning(
        '[Bird] Webhook on legacy path %s — assuming channel %s. '
        'Run sync_bird_channels to move this subscription.',
        request.path,
        default_channel_id,
    )
    return default_channel_id


def _channel_number(channel_id, platform):
    """
    The number a Bird channel sends from.

    Unknown channels are the shared company number's — only pooled per-driver
    numbers are tracked as VirtualNumber rows.
    """

    from blog.models import VirtualNumber

    field = 'voice_channel_id' if platform == 'voice' else 'sms_channel_id'
    virtual_number = VirtualNumber.objects.filter(**{field: channel_id}).first()

    return virtual_number.number if virtual_number else settings.BIRD_NUMBER


# =========================
# SMS WEBHOOK
# =========================
@csrf_exempt
@require_POST
@verify_bird_signature
def sms_webhook(request, channel_id=None):

    channel_id = _arriving_channel(channel_id, settings.BIRD_CHANNEL_ID, request)

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

    to_number, route = _resolve_route(from_number)

    if not to_number:
        return JsonResponse({'status': 'no mapping'})

    try:
        # Reply on the channel it arrived on, so the sender is answered from
        # the number they texted.
        send_bird_sms(to_number, message_text, channel_id=channel_id)

        logger.info(
            '[Bird SMS] %s → %s (channel=%s) via %s',
            from_number,
            to_number,
            channel_id,
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
@verify_bird_signature
def voice_webhook(request, channel_id=None):

    channel_id = _arriving_channel(channel_id, settings.BIRD_VOICE_CHANNEL_ID, request)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    logger.debug('[Bird Voice RAW] %s', json.dumps(data, indent=2))

    event = data.get('payload', {})
    call_id = event.get('id')
    from_number = event.get('from')
    call_status = event.get('status')

    if not call_id or not from_number:
        logger.warning('[Bird Voice] Missing call_id or from_number')
        return JsonResponse({'error': 'missing data'}, status=400)

    from_number = normalize_phone(from_number)

    if call_status not in ['starting', 'initiated']:
        logger.debug('[Bird Voice] Ignored status: %s', call_status)
        return JsonResponse({'status': 'ignored'})

    destination, route = _resolve_route(from_number)

    if not destination:
        logger.warning('[Bird Voice] No destination for %s', from_number)
        return JsonResponse({'status': 'no mapping'})

    # call_id belongs to the channel the call arrived on; bridging it through
    # any other channel is rejected, and that rejection is a 400 we swallow.
    bridge_from = _channel_number(channel_id, 'voice')

    url = (
        f'https://api.bird.com/workspaces/{settings.BIRD_WORKSPACE_ID}'
        f'/channels/{channel_id}/calls/{call_id}/bridge'
    )

    payload = {
        'to': destination,
        'from': bridge_from,
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
            '[Bird Voice] %s → %s (from=%s channel=%s) via %s',
            from_number,
            destination,
            bridge_from,
            channel_id,
            route
        )

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None

        if status_code == 400:
            # Kept as a 200 so Bird stops retrying a call that is already over,
            # but log enough to tell that apart from a genuine bridge failure —
            # a bare "already handled?" is how a broken leg stayed invisible.
            logger.warning(
                '[Bird Voice] 400 from Bird — call %s not bridged '
                '(%s → %s from=%s channel=%s): %s',
                call_id,
                from_number,
                destination,
                bridge_from,
                channel_id,
                e.response.text if e.response else '',
            )
            return JsonResponse({'status': 'ok'})

        logger.error('[Bird Voice] HTTP error %s: %s', status_code, e)
        return JsonResponse({'error': 'bridge failed'}, status=500)

    except requests.RequestException as e:
        logger.error('[Bird Voice] Request error: %s', e)
        return JsonResponse({'error': 'bridge failed'}, status=500)

    return JsonResponse({'status': 'ok'})