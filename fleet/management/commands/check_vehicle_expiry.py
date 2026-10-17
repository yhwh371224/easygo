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

# 크론은 주 1회(월요일) 돈다. 만료 한 달 전부터 갱신할 때까지 매주 알린다.

class Command(BaseCommand):
    help = 'Telegram alert when fleet rego / inspection / green slip expiry is approaching'

    def add_arguments(self, parser):
        parser.add_argument('--within', type=int, default=30, help='만료까지 남은 일수가 이 이하면 알린다')
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
                if days_left > options['within']:
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
