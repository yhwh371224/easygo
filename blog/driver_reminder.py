"""픽업 2시간 전 배정 드라이버 알림 (알림만 — 확인 버튼/미확인 경고 없음).

흐름
  driver_pickup_reminder 크론(15분 간격)이 '픽업 2시간 전'이 된 배정 건을 찾아
  - 텔레그램을 연결한 드라이버 → 드라이버 봇 메시지([📋 Dashboard] 버튼만)
  - 연결 안 했거나 봇을 차단한 드라이버 → driver_contact 로 Twilio SMS
  둘 다 못 보내면(번호 없음/Twilio 실패) 관리자 텔레그램으로 전화하라고 알린다.

예전 확인(ack) 버튼이 달린 메시지가 남아 있을 수 있어 webhook 의 ack 처리는 남겨 둔다.

부킹별 Celery eta 예약을 쓰지 않는 이유는 arrival_reminder 와 같다: 서버가 매일
재부팅되면 eta 작업이 사라지고, 재배정·시간 변경을 따라가지 못한다. 매 실행마다
DB 로 다시 판단한다.

중복 방지는 driver_reminder_sent_to(처리한 드라이버)로 한다. 현재 driver 와 다르면
재배정된 것이라 새 드라이버에게 다시 보내고 확인 상태도 초기화한다.
"""

import logging
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from basecamp.modules.date_utils import format_pickup_time_12h

from utils import telegram_driver

logger = logging.getLogger(__name__)

DEFAULT_TZ = 'Australia/Sydney'
REMINDER_LEAD = timedelta(hours=2)
TIME_FORMATS = ('%H:%M', '%I:%M %p', '%H:%M:%S')

# 예전 알림 메시지의 확인 버튼 callback_data (webhook 호환용).
ACK_PREFIX = 'ack:'


def is_owner_driver(driver):
    from blog.models.booking import OWNER_DRIVER_NAMES
    return (getattr(driver, 'driver_name', None) or '').strip().lower() in OWNER_DRIVER_NAMES


def parse_time(raw):
    raw = (raw or '').strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def booking_tz(booking):
    region = getattr(booking, 'region', None)
    return pytz.timezone(getattr(region, 'timezone', None) or DEFAULT_TZ)


def pickup_datetime(booking):
    """지역 현지 시각의 aware datetime. 시각을 읽을 수 없으면 None."""
    parsed = parse_time(booking.pickup_time)
    if not (booking.pickup_date and parsed):
        return None
    return booking_tz(booking).localize(datetime.combine(booking.pickup_date, parsed))


def dashboard_url():
    return settings.SITE_URL.rstrip('/') + reverse('blog:driver_dashboard')


def dashboard_button_row():
    return [{'text': '📋 Open dashboard', 'url': dashboard_url()}]


def reminder_buttons(booking):
    return [dashboard_button_row()]


REMINDER_TEXT = 'EasyGo job in 2 hours.'


def build_message(booking, pickup_dt, now_dt):
    """텔레그램 — 한 줄만. 자세한 내용은 Dashboard 버튼으로 본다."""
    return f'🚐 {REMINDER_TEXT}'


def build_sms_message(booking, pickup_dt, now_dt):
    """1 segment 로 짧게. 이모지를 넣으면 UCS-2 로 바뀌어 요금이 늘어나니 넣지 말 것."""
    return REMINDER_TEXT



class ReminderRun:
    """한 번의 크론 실행. alerts 는 관리자 텔레그램으로 한 메시지에 묶어 보낸다."""

    def __init__(self, dry_run=False, now_fn=None, stdout=None):
        self.dry_run = dry_run
        self.now_fn = now_fn or timezone.now
        self.stdout = stdout
        self.alerts = []
        self.sent = 0

    def log(self, msg):
        if self.stdout:
            self.stdout.write(msg)

    def candidates(self):
        from blog.models import Post
        # 지역 시차가 있어도 오늘·내일 픽업이면 2시간 창을 모두 덮는다
        # (자정 직후 픽업은 전날 밤에 알림이 나가야 한다).
        today = timezone.localdate(self.now_fn())
        return (
            Post.objects.filter(
                pickup_date__range=[today - timedelta(days=1), today + timedelta(days=1)],
                driver__isnull=False,
                cancelled=False,
            )
            .select_related('driver', 'region')
            .order_by('pickup_date', 'pickup_time')
        )

    def run(self):
        now = self.now_fn()
        for booking in self.candidates():
            if is_owner_driver(booking.driver):
                continue
            if booking.driver_reminder_sent_to_id != booking.driver_id:
                self.maybe_send(booking, now)
        self.flush_alerts()
        return self.sent

    # ---------- 2시간 전 알림 ----------
    def maybe_send(self, booking, now):
        pickup_dt = pickup_datetime(booking)
        if pickup_dt is None:
            if booking.pickup_date != timezone.localdate(now):
                return
            # 시각을 못 읽으면 언제 보낼지 모른다. 한 번만 알리고 처리됨으로 표시.
            self.alerts.append(
                f'⚠️ 기사 알림 불가(픽업시각 해석 실패 "{booking.pickup_time}") | '
                f'{booking.driver.driver_name} | {booking.name} | #{booking.pk}'
            )
            self.mark_handled(booking, sent=False)
            return
        if not (pickup_dt - REMINDER_LEAD <= now < pickup_dt):
            return

        driver = booking.driver
        local_now = now.astimezone(pickup_dt.tzinfo)
        summary = f'{driver.driver_name} | #{booking.pk} {booking.name} | {pickup_dt:%H:%M}'

        if driver.telegram_chat_id and telegram_driver.is_configured():
            text = build_message(booking, pickup_dt, local_now)
            if self.dry_run:
                self.log(f'[dry-run] telegram → {driver.driver_name} ({driver.telegram_chat_id})\n{text}\n')
                self.sent += 1
                return
            try:
                telegram_driver.send_message(driver.telegram_chat_id, text, reminder_buttons(booking))
            except telegram_driver.TelegramDriverError as exc:
                logger.warning('[driver_reminder] telegram failed post=%s: %s', booking.pk, exc)
                if not exc.permanent:
                    # 일시 오류는 다음 실행(15분 뒤)에서 다시 시도한다.
                    self.alerts.append(f'❌ 기사 텔레그램 실패(재시도 예정) | {summary} | {exc}')
                    return
                # 봇 차단/잘못된 chat id — 재시도해도 같으니 SMS 로 대신 보낸다.
                self.alerts.append(f'⚠️ 기사 텔레그램 실패(봇 차단/연결 오류) → SMS 로 대체 | {summary} | {exc}')
            else:
                self.mark_handled(booking, sent=True)
                self.sent += 1
                self.alerts.append(f'🔔 기사 2시간 전 알림 발송(텔레그램) | {summary}')
                return

        self.send_sms(booking, pickup_dt, local_now, summary)

    def send_sms(self, booking, pickup_dt, local_now, summary):
        driver = booking.driver
        text = build_sms_message(booking, pickup_dt, local_now)
        if self.dry_run:
            self.log(f'[dry-run] sms → {driver.driver_name} ({driver.driver_contact})\n{text}\n')
            self.sent += 1
            return
        from blog import sms_utils
        sid = sms_utils.send_sms_notice(driver.driver_contact, text) if driver.driver_contact else None
        # SMS 실패는 재시도하지 않는다 — 잘못된 번호면 매번 같은 실패이고, Twilio 가
        # 실제로는 보냈는데 오류로 보인 경우 15분마다 중복 문자가 나간다.
        self.mark_handled(booking, sent=bool(sid))
        if sid:
            self.sent += 1
            self.alerts.append(f'🔔 기사 2시간 전 알림 발송(SMS) | {summary}')
        else:
            self.alerts.append(
                f'❌ 기사 2시간 전 SMS 실패 — 전화 필요 | {summary} | '
                f'번호: {driver.driver_contact or "없음"}'
            )

    def mark_handled(self, booking, sent):
        if self.dry_run:
            return
        from blog.models import Post
        # save() 대신 update() — post_save 시그널(캘린더 동기화 등)이 15분마다 돌지 않게.
        # 재배정이면 이전 드라이버의 확인 상태도 같이 지운다.
        Post.objects.filter(pk=booking.pk).update(
            driver_reminder_sent_to=booking.driver_id,
            driver_reminder_sent_at=timezone.now() if sent else None,
            driver_ack_at=None,
            driver_ack_alert_sent_at=None,
        )

    def flush_alerts(self):
        if not self.alerts:
            return
        if self.dry_run:
            self.log('[dry-run] staff alerts:\n' + '\n'.join(self.alerts))
            return
        from utils.telegram import send_telegram_sync
        try:
            send_telegram_sync('\n'.join(self.alerts))
        except Exception:
            logger.exception('[driver_reminder] staff telegram alert failed')


# ---------- 새 잡 오퍼 알림 ----------
# 관리자가 Post.candidate_drivers 에 드라이버를 추가하면(대시보드 'Available Jobs'에
# Accept 버튼이 뜬다) 그 드라이버에게 바로 알린다. 먼저 수락한 사람이 가져가므로
# 크론이 아니라 시그널 → Celery 로 즉시 보낸다.

OFFER_SIGNOFF = 'Thanks Peter'


def offer_greeting(driver):
    """'Hi Ali, Please check your dashboard. Thanks Peter' — 이름은 첫 단어만."""
    first = ((getattr(driver, 'driver_name', None) or '').strip().split() or ['there'])[0]
    return f'Hi {first}, Please check your dashboard. {OFFER_SIGNOFF}'


def build_offer_message(booking, driver):
    """짧게 — 인사말 + 날짜·시간과 고객 요청(아기 시트 등은 message 란에 들어온다)만. 나머지는 대시보드에서."""
    lines = [offer_greeting(driver),
             '',
             '🆕 New job available',
             f'{booking.pickup_date:%a %d %b} {format_pickup_time_12h(booking.pickup_time)}']
    note = (booking.message or '').strip()
    if note:
        if len(note) > 500:  # 텔레그램 4096자 제한 여유
            note = note[:500].rstrip() + '…'
        lines.append(note)
    return '\n'.join(lines)


def send_job_offers(post_id, driver_ids):
    """후보로 추가된 드라이버들에게 잡 오퍼 알림. 보낸 수를 돌려준다.

    텔레그램을 연결한 드라이버에게만 보낸다(SMS 대체 없음). 작업이 큐에서 도는 사이
    이미 배정·취소됐거나 후보에서 빠졌으면 보내지 않는다.
    미연결·오너 드라이버는 조용히 건너뛴다(관리자가 직접 배정하는 경로라 경고 불필요)."""
    from blog.models import Post
    if not telegram_driver.is_configured():
        return 0
    booking = Post.objects.filter(pk=post_id).first()
    if (booking is None or booking.driver_id or booking.cancelled
            or (booking.pickup_date and booking.pickup_date < timezone.localdate())):
        return 0
    drivers = booking.candidate_drivers.filter(pk__in=driver_ids).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id='')
    sent, failures = 0, []
    for driver in drivers:
        if is_owner_driver(driver):
            continue
        try:
            telegram_driver.send_message(driver.telegram_chat_id, build_offer_message(booking, driver),
                                         [dashboard_button_row()])
        except telegram_driver.TelegramDriverError as exc:
            logger.warning('[job_offer] send failed post=%s driver=%s: %s', post_id, driver.pk, exc)
            failures.append(f'{driver.driver_name}: {exc}')
            continue
        sent += 1
    if failures:
        from utils.telegram import send_telegram_sync
        try:
            send_telegram_sync(f'❌ 잡 오퍼 텔레그램 실패 | #{booking.pk} {booking.name}\n' + '\n'.join(failures))
        except Exception:
            logger.exception('[job_offer] staff telegram alert failed')
    return sent
