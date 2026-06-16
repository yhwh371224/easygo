from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import models
from blog.models import Post


class Command(BaseCommand):
    help = 'Mark other-driver cash bookings and fill paid with price (yesterday)'

    def handle(self, *args, **kwargs):
        yesterday = timezone.now().date() - timedelta(days=1)

        base = Post.objects.filter(
            pickup_date=yesterday,
            cancelled=False,
            cash=True,
        )

        # 1) driver가 본인 아닌 cash 건 → driver_collected_cash=True
        flagged = base.exclude(driver__driver_name__iexact='sam').update(
            driver_collected_cash=True
        )

        # 2) 위에서 표시된 건 중 paid 비어있으면 price로 채움
        qs = base.filter(
            paid__isnull=True,
            driver_collected_cash=True,
        )
        updated_count = qs.update(paid=models.F('price'))

        self.stdout.write(self.style.SUCCESS(
            f'Flagged {flagged} as driver-collected, filled paid on {updated_count}'
        ))