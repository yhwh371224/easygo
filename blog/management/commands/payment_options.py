from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from blog.models import Post
from utils.email import send_template_email


class Command(BaseCommand):
    help = 'Send reminder email + SMS to all unpaid future bookings'

    def handle(self, *args, **options):
        now = timezone.now()

        reminders = Post.objects.filter(
            pickup_date__gt=now,   # 미래 부킹만
            reminder=False,
            cancelled=False,
        ).exclude(
            Q(paid__isnull=False) & ~Q(paid__exact="")
        ).exclude(
            cash=True
        ).exclude(
            prepay=True
        )
        
        for notice in reminders:
            try:
                # 💰 총 금액 계산 (return 있으면 2배)
                if notice.return_pickup_date:
                    total_price = float(notice.price) * 2
                else:
                    total_price = notice.price

                # 1️⃣ 이메일 발송
                recipients = [addr for addr in [notice.email, notice.email1] if addr]
                if recipients:
                    send_template_email(
                        "Payment Method Reminder",
                        "html_email-payment-method.html",
                        {
                            "name": notice.name,
                            "email": notice.email,
                            "pickup_date": notice.pickup_date,
                            "return_pickup_date": notice.return_pickup_date,
                            "price": total_price,
                            "prepay": notice.prepay,
                        },
                        recipients,
                    )

                # 2️⃣ SMS 발송 
                # if notice.contact:
                #     sms_message = (
                #         f"EasyGo - Payment Method Reminder\n\n"
                #         f"Dear {notice.name},\n"
                #         f"We have sent you an email regarding your preferred payment method.\n"
                #         f"Please check the email and reply **via email only** to confirm.\n"
                #     )
                #     send_sms_notice(notice.contact, sms_message)

                #     if notice.direction == 'Pickup from Intl Airport':
                #         send_whatsapp_template(notice.contact, user_name=notice.name)

                # 3️⃣ pending 표시
                notice.pending = True
                notice.save()

            except Exception as e:
                print(f"Failed to send email/SMS for {notice.email}: {e}")

        self.stdout.write(self.style.SUCCESS("Reminder emails + SMS sent."))
