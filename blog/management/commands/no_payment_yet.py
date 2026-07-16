import logging

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from blog.models import Post
from main.settings import RECIPIENT_EMAIL
from utils.email import send_template_email, collect_recipients


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send reminders for payment'

    def get_display_date(self, booking):
        if booking.return_pickup_time == 'x':
            if booking.return_pickup_date and booking.return_pickup_date < date.today():
                return str(booking.pickup_date)
            else:
                return f"{booking.pickup_date} & {booking.return_pickup_date}"
        return str(booking.pickup_date)

    def handle(self, *args, **options):       
        today = date.today() 
        start_date = date.today() + timedelta(days=1)
        end_date = start_date + timedelta(days=21)

        bookings = Post.objects.filter(
            pickup_date__range=(start_date, end_date),
            cash=False,
            cancelled=False,
        )

        for booking in bookings:
            display_date = self.get_display_date(booking)  
            
            try: 
                # paid 값 float로 안전하게 변환
                price = float(booking.price or 0)
                paid = float(booking.paid or 0)

                # ----------------------------
                # 1. 결제 미완료 메일 (단계별 1회만 발송 — 이미 보낸 단계는 건너뜀)
                # ----------------------------
                if booking.paid is None or booking.paid == "" or paid == 0:
                    days_difference = (booking.pickup_date - start_date).days
                    if days_difference <= 2:
                        email_subject = "Urgent notice for payment"
                        template = "html_email-nopayment-today.html"
                        sent_field = "no_payment_urgent_sent_at"
                    else:
                        email_subject = "Payment notice"
                        template = "html_email-nopayment.html"
                        sent_field = "no_payment_notice_sent_at"

                    if getattr(booking, sent_field) is not None:
                        continue

                    send_template_email(
                        email_subject,
                        template,
                        {
                            'booker_name': booking.booker_name,
                            'name': booking.name,
                            'email': booking.email,
                            'price': booking.price,
                            'pickup_date': booking.pickup_date,
                            'return_pickup_date': booking.return_pickup_date,
                            'display_date': display_date,
                            "prepay": booking.prepay,
                        },
                        collect_recipients(booking.booker_email or booking.email)
                    )
                    setattr(booking, sent_field, timezone.now())
                    booking.save(update_fields=[sent_field])

                # ----------------------------
                # 2. 결제 차액 메일 (디파짓으로 예고된 부분결제는 제외, 진짜 차액만
                #    픽업 2일 전 1회 + 1일 전 최종 경고 1회 — 매일 재발송하지 않음)
                # ----------------------------
                elif 0 < paid < price:
                    deposit_due = booking.deposit_amount_due
                    deposit_satisfied = deposit_due is not None and paid >= float(deposit_due)
                    if deposit_satisfied:
                        continue

                    diff = round(price - paid, 2)
                    days_before_pickup = (booking.pickup_date - today).days

                    if days_before_pickup == 2 and booking.discrepancy_notice_sent_at is None:
                        send_template_email(
                            "Urgent notice for payment discrepancy",
                            "html_email-response-discrepancy.html",
                            {
                                'booker_name': booking.booker_name,
                                'name': booking.name,
                                'price': booking.price,
                                'paid': booking.paid,
                                'diff': diff,
                                'pickup_date': booking.pickup_date,
                                'return_pickup_date': booking.return_pickup_date,
                                'display_date': display_date,
                            },
                            collect_recipients(booking.booker_email or booking.email)
                        )
                        booking.discrepancy_notice_sent_at = timezone.now()
                        booking.save(update_fields=['discrepancy_notice_sent_at'])

                    elif days_before_pickup == 1 and booking.discrepancy_final_sent_at is None:
                        send_template_email(
                            "Final notice: outstanding balance on your booking",
                            "html_email-response-discrepancy-final.html",
                            {
                                'booker_name': booking.booker_name,
                                'name': booking.name,
                                'price': booking.price,
                                'paid': booking.paid,
                                'diff': diff,
                                'pickup_date': booking.pickup_date,
                                'return_pickup_date': booking.return_pickup_date,
                                'display_date': display_date,
                            },
                            collect_recipients(booking.booker_email or booking.email)
                        )
                        booking.discrepancy_final_sent_at = timezone.now()
                        booking.save(update_fields=['discrepancy_final_sent_at'])

            except Exception as e:
                logger.error(f"Failed to send email for booking {booking.id} ({booking.email}): {e}")
                self.stdout.write(self.style.ERROR(f"Failed to send email for {booking.email}: {e}"))

        self.stdout.write(self.style.SUCCESS('No_payment_yet emailed successfully'))


