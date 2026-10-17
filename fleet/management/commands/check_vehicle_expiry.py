import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from fleet.models import Vehicle
from utils.telegram import send_telegram_sync


logger = logging.getLogger(__name__)

# (필드명, 표시 이름)
EXPIRY_FIELDS = [
    ('rego_expiry_date', '등록(Rego)'),
    ('inspection_date', '검사(Inspection)'),
    ('green_slip_expiry_date', '그린슬립(CTP)'),
]

# 남은 일수가 이 값들과 정확히 같은 날에만 알린다. 매일 보내면 한 달 내내 같은
# 알림이 와서 무시하게 된다. 만료일이 지난 뒤에는 갱신할 때까지 매일 보낸다.
NOTIFY_DAYS = (30, 14, 7, 3, 1, 0)


class Command(BaseCommand):
    help = 'Telegram alert when fleet rego / inspection / green slip expiry is approaching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help='알림 일자와 상관없이 --within 일 이내 만료 건을 전부 보낸다 (수동 점검용)',
        )
        parser.add_argument('--within', type=int, default=30)
        parser.add_argument('--dry-run', action='store_true', help='텔레그램 대신 화면에만 출력')

    def handle(self, *args, **options):
        today = timezone.localdate()
        lines = []

        for vehicle in Vehicle.objects.filter(is_active=True):
            for field, label in EXPIRY_FIELDS:
                expiry = getattr(vehicle, field)
                if not expiry:
                    continue
                days_left = (expiry - today).days

                if options['all']:
                    due = days_left <= options['within']
                else:
                    due = days_left < 0 or days_left in NOTIFY_DAYS
                if not due:
                    continue

                if days_left < 0:
                    status = f'🔴 {-days_left}일 지남'
                elif days_left == 0:
                    status = '🔴 오늘 만료'
                elif days_left <= 7:
                    status = f'🟠 {days_left}일 남음'
                else:
                    status = f'🟡 {days_left}일 남음'
                lines.append(f'{vehicle.plate_number} {label} {expiry:%d/%m/%Y} — {status}')

        if not lines:
            self.stdout.write('만료 임박 항목 없음')
            return

        message = '🚐 차량 만료 알림\n' + '\n'.join(lines)
        self.stdout.write(message)
        if not options['dry_run']:
            send_telegram_sync(message)
