"""당일 공항 도착 건 리마인더 — 도착 예정시각 1시간 전 발송.

도착 손님은 아침에 메일을 받아도 비행 중이라 못 보고, 착륙 직후 기사/미팅포인트
정보를 다시 찾느라 헤맨다. 그래서 도착 건은 아침 Reminder-Today 대신 이 커맨드가
'도착 1시간 전'에 한 번 보낸다(booking_reminder는 도착 건을 당일 메일에서 제외).

기준 시각은 고객이 입력한 flight_time(도착 예정시각)이다. 실시간 항공편 추적을
붙이지 않았으므로 지연/조기 도착은 반영되지 않는다.

크론 — 실제 도착은 02~22시에만 있으므로(발송창 01~21시) 새벽엔 돌릴 필요가 없다.
발송 시각은 "창이 열린 뒤 첫 실행"이라 30분 간격이면 도착 60~30분 전에 나간다.

    */30 1-22 * * * .../python manage.py arrival_reminder >> logs/arrival_reminder.log 2>&1

부킹별 정시 예약(celery eta 등)을 쓰지 않는 이유: 이 서버는 매일 01:20에 재부팅되고
celery의 eta 작업은 워커 메모리에 있어 재부팅이면 조용히 사라진다. 손님이 비행 중이라
안 갔는지 알 방법도 없는 메일이라, 매 실행마다 DB에서 다시 판단하고 놓치면 다음 실행이
복구하는 쪽을 택했다. 도착 예약의 약 2%는 당일에 들어오기도 한다(새벽에 미리 뽑아두는
방식으로는 잡히지 않는다).
"""

import logging
from datetime import datetime, timedelta

import pytz
from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.blog_utils import assign_default_driver_if_missing
from blog.models import Post
from basecamp.modules.date_utils import format_pickup_time_12h
from utils import booking_helper
from utils.booking_helper import build_reminder_context
from utils.direction_utils import airport_arrival_q
from utils.email import collect_recipients, send_template_email
from utils.telegram import send_telegram_sync

logger = logging.getLogger(__name__)

DEFAULT_TZ = 'Australia/Sydney'
DEFAULT_LEAD_MINUTES = 60
# 발송이 이만큼 늦으면(크론 중단, 당일 늦게 들어온 예약 등) 보내되 텔레그램으로 알린다.
# 크론 간격(30분)보다 넉넉히 커야 한다 — 정상 실행에서도 창이 열린 직후를 놓치면
# 다음 실행까지 최대 한 간격이 밀리기 때문에, 그걸 지연으로 알리면 매일 울린다.
LATE_ALERT_MINUTES = 45
TIME_FORMATS = ('%H:%M', '%I:%M %p', '%H:%M:%S')

SUBJECT = 'Reminder-Today'


def current_time(tz):
    """지역 현지 시각. 테스트에서 시각을 고정할 수 있도록 함수로 분리."""
    return datetime.now(tz)


class Command(BaseCommand):
    help = "Send today's airport-arrival reminder ~1h before the flight's scheduled arrival."

    def add_arguments(self, parser):
        parser.add_argument(
            '--lead-minutes',
            type=int,
            default=DEFAULT_LEAD_MINUTES,
            help=f'도착 예정시각 몇 분 전에 보낼지 (기본 {DEFAULT_LEAD_MINUTES}).',
        )
        parser.add_argument(
            '--ids',
            type=str,
            help='콤마구분 booking id 목록 — 시간 창/중복방지 무시하고 즉시 재발송.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='발송 없이 대상만 출력.',
        )

    # =========================
    # ENTRY
    # =========================
    def handle(self, *args, **options):
        self.lead = timedelta(minutes=options['lead_minutes'])
        self.dry_run = options['dry_run']
        self.alerts = []

        ids_raw = options.get('ids')
        if ids_raw:
            target_ids = [int(i.strip()) for i in ids_raw.split(',') if i.strip()]
            self.refresh_meeting_points()
            sent = 0
            for booking in Post.objects.filter(id__in=target_ids).select_related(
                    'driver', 'region', 'terminal_pickup_point'):
                if self.send_one(booking, force=True):
                    sent += 1
            self.stdout.write(f'Forced resend: {sent}/{len(target_ids)}')
            self.flush_alerts()
            return

        # 이 커맨드는 몇 분마다 돌지만 실제 발송은 하루 몇 건뿐이다.
        # 대상이 없으면 가벼운 조회 두어 번만 하고 끝낸다.
        due = list(self.due_bookings())
        if not due:
            self.stdout.write('No arrival reminders due.')
            self.flush_alerts()
            return

        # 미팅포인트(터미널 픽업 지점)는 당일 기사/편수 기준으로 배정되므로
        # 메일에 넣기 전에 최신화한다. booking_reminder / send_arrivals와 동일.
        if self.refresh_meeting_points():
            for booking, *_ in due:
                booking.refresh_from_db()

        sent = 0
        for booking, due_at, now_dt, source in due:
            late_by = now_dt - due_at
            if late_by > timedelta(minutes=LATE_ALERT_MINUTES):
                self.alerts.append(
                    f'⏰ 도착 리마인더 지연 발송 {int(late_by.total_seconds() // 60)}분 '
                    f'| {booking.name} | #{booking.id} | {source}'
                )
            if self.send_one(booking):
                sent += 1

        self.stdout.write(f'Arrival reminders sent: {sent}')
        self.flush_alerts()

    def refresh_meeting_points(self):
        """dry-run은 DB를 건드리지 않는다 — 이 함수는 terminal_pickup_point를 저장한다."""
        if self.dry_run:
            return False
        booking_helper.update_meeting_point_for_arrivals()
        return True

    # =========================
    # 대상 선정
    # =========================
    def due_bookings(self):
        """발송 시각이 된 오늘 도착 건을 (booking, due_at, now, anchor_source)로 내보낸다."""
        from regions.models import Region

        # 지역마다 현지 시각이 다르다. region=None은 지역 배정 전 레거시 예약.
        region_tz_pairs = [
            (r, pytz.timezone(r.timezone or DEFAULT_TZ))
            for r in Region.objects.filter(is_active=True).only('id', 'timezone')
        ]
        region_tz_pairs.append((None, pytz.timezone(DEFAULT_TZ)))

        for region, tz in region_tz_pairs:
            now_dt = current_time(tz)

            queryset = (
                Post.objects.filter(region=region, pickup_date=now_dt.date())
                .filter(airport_arrival_q())
                .filter(arrival_reminder_sent_at__isnull=True)
                .exclude(cancelled=True)
                .exclude(pending=True)
                .exclude(no_email_reminder=True)
                .select_related('driver', 'region', 'terminal_pickup_point')
            )

            for booking in queryset:
                anchor, source = self.anchor_time(booking, tz)
                if anchor is None:
                    self.alerts.append(
                        f'⚠️ 도착 리마인더 발송 불가(시각 없음) | {booking.name} | '
                        f'#{booking.id} | {booking.flight_number or "편명없음"}'
                    )
                    logger.warning(
                        '[arrival_reminder] id=%s — no flight_time/pickup_time, skipped', booking.id
                    )
                    continue

                due_at = anchor - self.lead
                if now_dt < due_at:
                    continue

                yield booking, due_at, now_dt, source

    def anchor_time(self, booking, tz):
        """기준 시각(도착 예정시각). 없으면 픽업시각으로 폴백한다.

        폴백을 두는 이유: 도착 건은 이 메일이 아침 메일을 '대체'하기 때문에,
        flight_time이 비어 있다고 스킵하면 그 손님은 당일 메일을 아예 못 받는다.
        """
        for value, source in ((booking.flight_time, 'flight_time'),
                              (booking.pickup_time, 'pickup_time')):
            parsed = self.parse_time(value)
            if parsed:
                naive = datetime.combine(booking.pickup_date, parsed)
                return tz.localize(naive), source
        return None, None

    @staticmethod
    def parse_time(raw):
        raw = (raw or '').strip()
        if not raw:
            return None
        for fmt in TIME_FORMATS:
            try:
                return datetime.strptime(raw, fmt).time()
            except ValueError:
                continue
        return None

    # =========================
    # 발송
    # =========================
    def send_one(self, booking, force=False):
        # 수신거부는 --ids 강제 재발송으로도 뚫지 않는다(고객이 끈 것).
        if getattr(booking, 'no_email_reminder', False):
            logger.info('[arrival_reminder] SKIP id=%s — no_email_reminder', booking.id)
            return False
        if booking.arrival_reminder_sent_at and not force:
            logger.info('[arrival_reminder] SKIP id=%s — already sent', booking.id)
            return False

        driver = assign_default_driver_if_missing(booking, dry_run=self.dry_run)
        if not driver:
            # 기사 없이도 미팅포인트/편명 안내는 나가는 게 낫다(send_arrivals와 동일 판단).
            logger.warning(
                '[arrival_reminder] id=%s — no driver and no default driver for region=%s',
                booking.id, booking.region_id,
            )
            self.alerts.append(f'🚕 기사 미배정 상태로 도착 리마인더 발송 | {booking.name} | #{booking.id}')

        recipients = collect_recipients(booking.email, booking.email1)
        if not recipients:
            logger.warning('[arrival_reminder] SKIP id=%s — no recipients', booking.id)
            self.alerts.append(f'✉️ 수신자 없음 | {booking.name} | #{booking.id}')
            return False

        template_name = (
            'emails/driver_details.html' if booking.terminal_pickup_point else 'html_email-today.html'
        )
        context = build_reminder_context(
            booking, format_pickup_time_12h(booking.pickup_time), driver
        )

        if self.dry_run:
            self.stdout.write(
                f'[dry-run] #{booking.id} {booking.name} flight={booking.flight_time} '
                f'-> {recipients} ({template_name})'
            )
            return True

        try:
            send_template_email(SUBJECT, template_name, context, recipients, fail_silently=False)
        except Exception:
            logger.exception('[arrival_reminder] send failed id=%s', booking.id)
            self.alerts.append(f'❌ 도착 리마인더 발송 실패 | {booking.name} | #{booking.id}')
            return False

        # save() 대신 queryset.update() — post_save 시그널(캘린더 재동기화,
        # 리턴트립 처리, pending 재계산)이 10분마다 헛돌지 않게 한다.
        booking.arrival_reminder_sent_at = timezone.now()
        Post.objects.filter(pk=booking.pk).update(
            arrival_reminder_sent_at=booking.arrival_reminder_sent_at
        )
        logger.info('[arrival_reminder] SENT id=%s to %s (%s)', booking.id, recipients, template_name)
        return True

    # =========================
    # 알림
    # =========================
    def flush_alerts(self):
        if not self.alerts:
            return
        try:
            send_telegram_sync('\n'.join(self.alerts))
        except Exception as e:
            logger.error('[arrival_reminder] 텔레그램 알림 전송 실패: %s', e)
