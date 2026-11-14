"""픽업 2시간 전 드라이버 텔레그램 알림 + 확인(ack) 버튼.

흐름
  1. driver_pickup_reminder 크론(15분 간격)이 '픽업 2시간 전'이 된 배정 건을 찾아
     드라이버 봇으로 보낸다. 메시지에 [✅ Got it] / [📋 Dashboard] 버튼이 달린다.
  2. 드라이버가 Got it 을 누르면 webhook 이 Post.driver_ack_at 을 찍는다.
  3. 픽업 1시간 전까지(늦게 보낸 건은 발송 후 ACK_GRACE 뒤) 확인이 없으면 관리자
     텔레그램으로 경고한다 — 전화해 볼 시간이 남아 있을 때.

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
ACK_DEADLINE_LEAD = timedelta(hours=1)
# 픽업 직전에 배정돼 늦게 나간 알림은 드라이버가 볼 시간을 준 뒤에 경고한다.
ACK_GRACE = timedelta(minutes=20)
# 픽업이 지나도 이만큼은 미확인 경고를 낸다(그 뒤로는 의미 없음).
ACK_ALERT_CUTOFF = timedelta(hours=1)
TIME_FORMATS = ('%H:%M', '%I:%M %p', '%H:%M:%S')

ACK_PREFIX = 'ack:'

DIRECTION_LABELS = {
    'drop off to domestic airport': '✈️ To Domestic Airport',
    'drop off to intl airport': '✈️ To International Airport',
    'pickup from domestic airport': '✈️ From Domestic Airport',
    'pickup from intl airport': '✈️ From International Airport',
    'cruise or point to point': '🚗 Point to Point',
}


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
    return [
        [{'text': "✅ Got it — I'll be there", 'callback_data': f'{ACK_PREFIX}{booking.pk}'}],
        dashboard_button_row(),
    ]


def build_message(booking, pickup_dt, now_dt):
    """고객 이름·전화번호는 넣지 않는다 — 연락은 대시보드의 프록시 번호로 한다."""
    if pickup_dt.date() == now_dt.date():
        day = 'Today'
    elif pickup_dt.date() == now_dt.date() + timedelta(days=1):
        day = 'Tomorrow'
    else:
        day = pickup_dt.strftime('%a %d %b')
    lines = [
        '🚐 EasyGo job in 2 hours',
        f'#{booking.pk} · {day} {format_pickup_time_12h(booking.pickup_time)}',
    ]
    label = DIRECTION_LABELS.get((booking.direction or '').strip().lower())
    if label:
        lines.append(label)
    route = ' → '.join(p for p in (booking.start_point, booking.end_point) if p)
    if route:
        lines.append(route)
    if booking.suburb and booking.suburb not in route:
        lines.append(f'📍 {booking.suburb}')
    meta = []
    if booking.flight_number:
        meta.append(f'Flight {booking.flight_number}')
    if booking.no_of_passenger:
        meta.append(f'{booking.no_of_passenger} pax')
    if booking.no_of_baggage:
        meta.append(f'{booking.no_of_baggage} bags')
    if meta:
        lines.append(' · '.join(meta))
    lines += ['', 'Please tap ✅ to confirm. Full details & customer contact are on your dashboard.']
    return '\n'.join(lines)


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
            else:
                self.maybe_alert_unacked(booking, now)
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

        if not driver.telegram_chat_id:
            self.alerts.append(f'📵 텔레그램 미연결 — 2시간 전 알림 못 보냄, 전화 필요 | {summary}')
            self.mark_handled(booking, sent=False)
            return

        text = build_message(booking, pickup_dt, local_now)
        if self.dry_run:
            self.log(f'[dry-run] → {driver.driver_name} ({driver.telegram_chat_id})\n{text}\n')
            self.sent += 1
            return
        try:
            telegram_driver.send_message(driver.telegram_chat_id, text, reminder_buttons(booking))
        except telegram_driver.TelegramDriverError as exc:
            logger.warning('[driver_reminder] send failed post=%s: %s', booking.pk, exc)
            if exc.permanent:
                # 봇 차단/잘못된 chat id — 재시도해도 같은 실패라 처리됨으로 둔다.
                self.alerts.append(f'❌ 기사 알림 실패(봇 차단/연결 오류) — 전화 필요 | {summary} | {exc}')
                self.mark_handled(booking, sent=False)
            else:
                # 일시 오류는 다음 실행에서 다시 시도한다.
                self.alerts.append(f'❌ 기사 알림 실패(재시도 예정) | {summary} | {exc}')
            return
        self.mark_handled(booking, sent=True)
        self.sent += 1
        self.alerts.append(f'🔔 기사 2시간 전 알림 발송 | {summary}')

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

    # ---------- 미확인 경고 ----------
    def maybe_alert_unacked(self, booking, now):
        if (booking.driver_ack_at or booking.driver_ack_alert_sent_at
                or not booking.driver_reminder_sent_at):
            return
        pickup_dt = pickup_datetime(booking)
        if pickup_dt is None:
            return
        due = max(pickup_dt - ACK_DEADLINE_LEAD, booking.driver_reminder_sent_at + ACK_GRACE)
        if not (due <= now < pickup_dt + ACK_ALERT_CUTOFF):
            return
        driver = booking.driver
        self.alerts.append(
            f'🚨 기사 미확인 — 픽업 {pickup_dt:%H:%M}, 알림 확인 안 함. 전화해 주세요 | '
            f'{driver.driver_name} {driver.driver_contact or ""} | #{booking.pk} {booking.name}'
        )
        if not self.dry_run:
            from blog.models import Post
            Post.objects.filter(pk=booking.pk).update(driver_ack_alert_sent_at=timezone.now())

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
