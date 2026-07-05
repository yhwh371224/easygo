from django.core.management.base import BaseCommand
from blog.models import Post


class Command(BaseCommand):
    help = (
        'cash=True 이고 드라이버가 지정된 부킹을 모두 '
        'driver_collected_cash=True 로 표시 (회사 매출/GST 제외 처리).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 변경하지 않고 대상 건수만 출력.',
        )

    def handle(self, *args, **options):
        qs = Post.objects.filter(
            cash=True,
            driver__isnull=False,
            cancelled=False,
            driver_collected_cash=False,
        )

        count = qs.count()

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'[dry-run] {count} 건이 driver_collected_cash=True 로 변경될 예정.'
            ))
            return

        updated = qs.update(driver_collected_cash=True)
        self.stdout.write(self.style.SUCCESS(
            f'{updated} 건을 driver_collected_cash=True 로 표시함.'
        ))
