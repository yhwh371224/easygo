from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Q
from django.conf import settings
from blog.models import Post


class Command(BaseCommand):
    help = 'Send reminder email 2 days after booking if unpaid'

    def handle(self, *args, **options):
        today = date.today()

        reminders = Post.objects.filter(
            pickup_date__gt=today,   # 🔥 미래 부킹만
            reminder=False,
            cancelled=False,
        ).exclude(
            Q(paid__isnull=False) & ~Q(paid__exact="")
        ).exclude(
            cash=True
        ).exclude(
            prepay=True
        )

        # 이메일 발송
        for notice in reminders:
            try:
                html_content = render_to_string(
                    "basecamp/html_email-payment-method.html",
                    {
                        "name": notice.name,
                        "email": notice.email,
                    }
                )
                text_content = strip_tags(html_content)

                recipients = [addr for addr in [notice.email, notice.email1] if addr]
                if not recipients:
                    continue

                email = EmailMultiAlternatives(
                    "Payment reminder",
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    recipients
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

                # reminder 발송 완료 표시
                notice.pending = True
                notice.save()

            except Exception:
                # 실패해도 그냥 넘어감 (심플 버전)
                continue

        self.stdout.write(self.style.SUCCESS("Reminder method emails sent."))
