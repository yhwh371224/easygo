from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post


# python manage.py check_pending          # 일주일, 미입금·미발송만
# python manage.py check_pending --all     # 일주일 전체 부킹
# python manage.py check_pending --days 3  # 3일 이내


class Command(BaseCommand):
    help = "오늘부터 일주일 내 부킹 중 미입금(pending)·미발송(reminder) 건 확인"

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--all', action='store_true', help='조건 없이 전체')

    def handle(self, *args, **opts):
        today = date.today()
        end = today + timedelta(days=opts['days'])

        qs = Post.objects.filter(
            pickup_date__gte=today,
            pickup_date__lte=end,
            cancelled=False,
        )
        if not opts['all']:
            qs = qs.filter(pending=True, reminder=False)

        qs = qs.order_by('pickup_date', 'pickup_time')

        self.stdout.write(f"\n{today} ~ {end} | 총 {qs.count()}건\n")
        for p in qs:
            self.stdout.write(
                f"  #{p.id:<5} {str(p.pickup_date)} {p.pickup_time or '':<8} "
                f"{p.name:<20} pending={p.pending} reminder={p.reminder}"
            )