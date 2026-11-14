"""드라이버 봇 webhook — /start <token> 연결과 ✅ 확인 버튼.

텔레그램은 setWebhook 때 준 secret_token 을 X-Telegram-Bot-Api-Secret-Token 헤더로
돌려준다. 시크릿이 설정 안 됐거나 다르면 거절한다(fail closed).

처리한 업데이트에는 항상 200 을 준다 — 200 이 아니면 텔레그램이 같은 업데이트를
계속 재전송한다.
"""

import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from blog.driver_reminder import ACK_PREFIX, dashboard_button_row
from utils import telegram_driver

logger = logging.getLogger(__name__)

NOT_LINKED_REPLY = (
    "Hi! To get EasyGo job reminders here, open your driver dashboard and tap "
    "'Connect Telegram'."
)


@csrf_exempt
@require_POST
def telegram_driver_webhook(request):
    secret = settings.TELEGRAM_DRIVER_WEBHOOK_SECRET
    given = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if not secret or not hmac.compare_digest(given, secret):
        return HttpResponseForbidden()
    try:
        update = json.loads(request.body or b'{}')
    except ValueError:
        return HttpResponse(status=200)

    try:
        if 'callback_query' in update:
            handle_callback(update['callback_query'])
        elif 'message' in update:
            handle_message(update['message'])
    except telegram_driver.TelegramDriverError:
        logger.warning('[driver_bot] reply failed', exc_info=True)
    except Exception:
        logger.exception('[driver_bot] update handling failed')
    return HttpResponse(status=200)


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except telegram_driver.TelegramDriverError:
        logger.warning('[driver_bot] %s failed', getattr(fn, '__name__', fn), exc_info=True)


def handle_message(message):
    from blog.models import Driver

    chat = message.get('chat') or {}
    if chat.get('type') != 'private':
        return
    chat_id = str(chat.get('id'))
    text = (message.get('text') or '').strip()

    if text.startswith('/start'):
        parts = text.split(maxsplit=1)
        token = parts[1].strip() if len(parts) > 1 else ''
        driver = Driver.objects.filter(telegram_link_token=token).first() if token else None
        if driver:
            # 토큰은 1회용 — 연결과 동시에 지운다.
            Driver.objects.filter(pk=driver.pk).update(
                telegram_chat_id=chat_id, telegram_link_token=None)
            _safe(telegram_driver.send_message, chat_id,
                  f"✅ Connected, {driver.driver_name or 'driver'}! "
                  "You'll get a reminder here 2 hours before each pickup — "
                  "please tap ✅ on it to confirm.")
            from blog.tasks import send_telegram_task
            send_telegram_task.delay(f'🔗 기사 텔레그램 연결됨: {driver.driver_name} (#{driver.pk})')
            return
        if Driver.objects.filter(telegram_chat_id=chat_id).exists():
            _safe(telegram_driver.send_message, chat_id,
                  "You're already connected. Job reminders will arrive here.")
            return

    _safe(telegram_driver.send_message, chat_id, NOT_LINKED_REPLY)


def handle_callback(cq):
    from blog.models import Post

    cq_id = cq.get('id')
    data = cq.get('data') or ''
    message = cq.get('message') or {}
    chat_id = str((message.get('chat') or {}).get('id', ''))
    if not data.startswith(ACK_PREFIX):
        _safe(telegram_driver.answer_callback, cq_id)
        return
    try:
        post_id = int(data[len(ACK_PREFIX):])
    except ValueError:
        _safe(telegram_driver.answer_callback, cq_id)
        return

    post = Post.objects.select_related('driver').filter(pk=post_id).first()
    # 버튼을 누른 채팅이 지금 배정된 드라이버의 채팅인지 확인한다 — 재배정됐거나
    # 취소됐으면 옛 메시지의 버튼은 무효.
    if (post is None or post.cancelled or post.driver is None
            or post.driver.telegram_chat_id != chat_id):
        _safe(telegram_driver.answer_callback, cq_id,
              'This job is no longer assigned to you. Please check your dashboard.')
        return

    now = timezone.now()
    first_ack = Post.objects.filter(pk=post.pk, driver_ack_at__isnull=True).update(driver_ack_at=now)
    _safe(telegram_driver.answer_callback, cq_id, 'Thanks — confirmed!')

    if message.get('message_id') and message.get('text'):
        local = timezone.localtime(now)
        _safe(telegram_driver.edit_message, chat_id, message['message_id'],
              f"{message['text']}\n\n✅ Confirmed {local:%I:%M %p}",
              [dashboard_button_row()])

    # 이미 미확인 경고가 나갔다면, 관리자가 헛걸음(전화)하지 않게 늦은 확인도 알린다.
    if first_ack and post.driver_ack_alert_sent_at:
        from blog.tasks import send_telegram_task
        send_telegram_task.delay(
            f'✅ 늦은 확인: {post.driver.driver_name} | #{post.pk} {post.name} | {post.pickup_time}')
