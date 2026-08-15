import logging
from django.core.management.base import BaseCommand
from blog.models import Post
from django.utils import timezone
from main.settings import RECIPIENT_EMAIL
from utils.command_alerts import TelegramAlertMixin
from utils.email import send_template_email


logger = logging.getLogger(__name__)


class Command(TelegramAlertMixin, BaseCommand):
    alert_header = 'confirm_booking 실패'

    help = 'Send booking confirmation'

    def handle(self, *args, **options):
        self.send_email()

    def send_email(self):
        current_datetime = timezone.localtime(timezone.now())
        posts = Post.objects.filter(created__date=current_datetime.date())

        if posts.exists():
            self.send_email_task(posts, "html_email-confirmation.html", "EasyGo Booking confirmation")

    def send_email_task(self, posts, template_name, subject):
        to_update = []
        email_tasks = []

        for post in posts:
            if not post.sent_email:
                post.sent_email = True
                to_update.append(post)

                context = {
                    'company_name': post.company_name,
                    'booker_name': post.booker_name,
                    'name': post.name,
                    'contact': post.contact,
                    'email': post.email,
                    'email1': post.email1,
                    'pickup_date': post.pickup_date,
                    'flight_number': post.flight_number,
                    'flight_time': post.flight_time,
                    'pickup_time': post.pickup_time,
                    'return_direction': post.return_direction,
                    'return_pickup_date': post.return_pickup_date,
                    'return_flight_number': post.return_flight_number,
                    'return_flight_time': post.return_flight_time,
                    'return_pickup_time': post.return_pickup_time,
                    'direction': post.direction,
                    'street': post.street,
                    'suburb': post.suburb,
                    'no_of_passenger': post.no_of_passenger,
                    'no_of_baggage': post.no_of_baggage,
                    'message': post.message,
                    'notice': post.notice,
                    'price': post.price,
                    'paid': post.paid,
                    'cash': post.cash,
                    'prepay': post.prepay,
                    'reminder': post.reminder,
                    'extra_stop_addresses': post.extra_stop_addresses or [],
                }
                if post.booker_email:
                    recipients = [post.booker_email, RECIPIENT_EMAIL]
                else:
                    recipients = [r for r in [post.email, post.email1, RECIPIENT_EMAIL] if r]
                email_tasks.append((post, (subject, template_name, context, recipients)))

        if to_update:
            Post.objects.bulk_update(to_update, ['sent_email'], batch_size=50)
            for post, args in email_tasks:
                # 한 건이 실패해도 나머지는 계속 보낸다. 예외를 그대로 두면 첫 실패에서
                # 루프가 끊겨 뒤 예약들은 sent_email=True 인 채 메일이 아예 안 나간다.
                try:
                    send_template_email(*args)
                except Exception as e:
                    logger.exception('confirm_booking: failed for Post pk=%s', post.pk)
                    # sent_email 은 이미 True 로 저장된 뒤라 다음 실행에서 재시도되지 않는다.
                    # 이 알림을 놓치면 그 손님은 확인 메일을 영영 못 받는다.
                    self.alerts.append(
                        f"❌ 예약확인 메일 발송 실패(재시도 없음) | {post.name} | "
                        f"#{post.id} | {str(e)[:120]}"
                    )
