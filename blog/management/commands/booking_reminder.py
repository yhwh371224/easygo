import logging
from collections import defaultdict
from datetime import timedelta
from itertools import zip_longest

from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils import booking_helper
from utils.booking_helper import build_reminder_context
from blog.blog_utils import assign_default_driver_if_missing
from utils.direction_utils import airport_arrival_q
from utils.email import send_template_email, collect_recipients
from utils.telegram import send_telegram_sync
from basecamp.modules.date_utils import format_pickup_time_12h

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send booking reminder emails for upcoming flights'

    def add_arguments(self, parser):
        parser.add_argument(
            '--today',
            action='store_true',
            help='Send only today\'s reminder emails',
        )
        parser.add_argument(
            '--ids',
            type=str,
            help='콤마구분 booking id 목록 (해당 id만 today reminder 재발송)',
        )

    def handle(self, *args, **options):
        # 제목별 발송 성공 id. 누락 탐지가 Reminder-Today 뿐 아니라 모든 단계를
        # 보도록 제목을 키로 둔다(2026-08-16 SMTP 장애 때 Today 외 8건이 조용히 실패).
        self._sent_ids = defaultdict(set)
        self._expected_ids = {}

        ids_raw = options.get('ids')
        if ids_raw:
            target_ids = [int(i.strip()) for i in ids_raw.split(',') if i.strip()]
            today = timezone.localdate()
            qs = Post.objects.filter(id__in=target_ids).select_related('driver')
            self.send_email_task(qs, "html_email-today.html", "Reminder-Today", today)
            # 수신거부 건은 애초에 보내지 않는 게 정상이라 누락으로 세지 않는다.
            expected = set(
                Post.objects.filter(id__in=target_ids)
                .exclude(no_email_reminder=True)
                .values_list('id', flat=True)
            )
            self.report_missing("재발송 후에도 누락", expected - self._sent_ids["Reminder-Today"])
            return

        # --- 오늘 국제선 도착 예약 meeting_point 업데이트 ---
        booking_helper.update_meeting_point_for_arrivals()

        reminder_intervals = [0, 1, 2, 3, 7, -5]  # -5: 5일 전 픽업 완료 고객 리뷰 요청
        templates = [
            "html_email-today.html",
            "html_email-tomorrow.html",
            "html_email-arrival-2days.html",
            "html_email-upcoming3.html",
            "html_email-upcoming7.html",
            "html_email-yesterday.html",
        ]
        subjects = [
            "Reminder-Today",
            "Reminder-Tomorrow",
            "Reminder-Arrival-2days",
            "Reminder-3days",
            "Reminder-7days",
            "Review-EasyGo",
        ]

        if options['today']:
            self.send_email(0, "html_email-today.html", "Reminder-Today")
        else:
            for interval, template, subject in zip_longest(reminder_intervals, templates, subjects, fillvalue=""):
                self.send_email(interval, template, subject)

        # --- 단계별 누락 탐지 ---
        # 발송 대상으로 뽑혔는데 성공 기록이 없는 건 = 발송 실패·수신자 없음·예외.
        for subject, expected in self._expected_ids.items():
            self.report_missing(f"{subject} 누락", expected - self._sent_ids[subject])

    def report_missing(self, title, missing_ids):
        if not missing_ids:
            return
        lines = [f"⚠️ {title} {len(missing_ids)}건"]
        for p in Post.objects.filter(id__in=missing_ids):
            lines.append(f"• {p.name} | {p.email} | #{p.id} | {p.pickup_date}")
        try:
            send_telegram_sync("\n".join(lines))
        except Exception as e:
            logger.error(f"[{title}] 텔레그램 알림 전송 실패: {e}")

    def send_email(self, date_offset, template_name, subject):
        target_date = timezone.localdate() + timedelta(days=date_offset)
        booking_reminders = (
            Post.objects.filter(pickup_date=target_date)
            .exclude(cancelled=True)
            .exclude(pending=True)
            .select_related('driver')
        )
        if subject == "Reminder-Today":
            # 공항 도착 건의 당일 메일은 arrival_reminder 커맨드가 도착 1시간 전에
            # 따로 보낸다(비행 중이라 아침 메일을 못 보는 문제). 여기서 보내면 중복.
            booking_reminders = booking_reminders.exclude(airport_arrival_q())
        if subject == "Reminder-Arrival-2days":
            booking_reminders = booking_reminders.filter(direction__istartswith="pickup")
        if subject == "Review-EasyGo":
            # 리뷰 요청 거부(no_review) 고객 제외
            booking_reminders = booking_reminders.exclude(no_review=True)
        # 수신거부 건은 send_email_task 가 의도적으로 건너뛰므로 기대 집합에서도 뺀다.
        # (넣어두면 매일 "누락"으로 잡혀 알림이 늑대소년이 된다)
        self._expected_ids[subject] = set(
            booking_reminders.exclude(no_email_reminder=True).values_list('id', flat=True)
        )
        self.send_email_task(booking_reminders, template_name, subject, target_date)

    def send_email_task(self, booking_reminders, template_name, subject, target_date):
        for booking_reminder in booking_reminders:
            if getattr(booking_reminder, "no_email_reminder", False):
                logger.info(f"[{subject}] SKIP id={booking_reminder.id} — no_email_reminder set for {booking_reminder.email}")
                continue
            if subject == "Review-EasyGo" and getattr(booking_reminder, "no_review", False):
                logger.info(f"[{subject}] SKIP id={booking_reminder.id} — no_review set for {booking_reminder.email}")
                continue
            try:
                logger.info(f"[{subject}] Processing booking id={booking_reminder.id} email={booking_reminder.email} booker_email={booking_reminder.booker_email}")

                # 도착("Pickup from") 손님이 driver 미배정이면 지역 기본 드라이버를
                # 자동 배정해서 발송한다 (전에는 여기서 skip하고 send_arrivals가 처리했지만,
                # driver 없이도 send_arrivals가 돌기 때문에 driver 상세 정보 없이 메일이
                # 나가거나, 아예 다른 이유로 send_arrivals에서도 누락되면 조용히 빠지는 문제가 있었음).
                is_arrival = "pickup from" in (booking_reminder.direction or "").lower()
                if not booking_reminder.driver and subject == "Reminder-Today" and is_arrival:
                    driver = assign_default_driver_if_missing(booking_reminder)
                    if not driver:
                        logger.warning(f"[{subject}] SKIP id={booking_reminder.id} — no driver and no default driver found for region={booking_reminder.region}")
                        continue

                logger.info(f"[{subject}] id={booking_reminder.id} terminal_pickup_point={booking_reminder.terminal_pickup_point}")

                driver = getattr(booking_reminder, "driver", None)
                pickup_time_12h = format_pickup_time_12h(booking_reminder.pickup_time)
                context = build_reminder_context(booking_reminder, pickup_time_12h, driver)

                booker_email = booking_reminder.booker_email
                is_today = subject == "Reminder-Today"
                is_tomorrow = subject == "Reminder-Tomorrow"
                is_arrival_2days = subject == "Reminder-Arrival-2days"
                is_upcoming3 = subject == "Reminder-3days"
                is_upcoming7 = subject == "Reminder-7days"
                is_review = subject == "Review-EasyGo"

                if is_review:
                    # 리뷰 요청: booker_email이 있으면 booker에게, 없으면 실제 탑승자에게
                    if booker_email:
                        email_recipients = collect_recipients(booker_email)
                    else:
                        email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)
                elif booker_email:
                    if is_today:
                        email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)
                    elif is_tomorrow or is_arrival_2days:
                        email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1, booker_email)
                    else:
                        # 7days: booker_email만
                        email_recipients = collect_recipients(booker_email)
                else:
                    email_recipients = collect_recipients(booking_reminder.email, booking_reminder.email1)

                logger.info(f"[{subject}] id={booking_reminder.id} email_recipients={email_recipients}")

                if is_today:
                    if booking_reminder.terminal_pickup_point:
                        today_template = "emails/driver_details.html"
                    else:
                        today_template = "html_email-today.html"
                    template_name = today_template
                    logger.info(f"[{subject}] id={booking_reminder.id} template={template_name}")

                if not email_recipients:
                    logger.warning(f"[{subject}] SKIP id={booking_reminder.id} — no recipients (email={booking_reminder.email} email1={booking_reminder.email1} booker_email={booker_email})")
                    continue

                try:
                    send_template_email(subject, template_name, context, email_recipients, fail_silently=False)
                    logger.info(
                        f"Successfully sent '{subject}' email to {email_recipients} for pickup on {target_date}"
                    )
                    self._sent_ids[subject].add(booking_reminder.id)
                except Exception as e:
                    logger.error(f"Failed to send email to {email_recipients}: {str(e)}")

            except Exception as e:
                logger.exception(
                    f"FAILED booking_reminder.id={booking_reminder.id} error={str(e)}"
                )
                continue