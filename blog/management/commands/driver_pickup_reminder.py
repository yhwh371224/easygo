"""픽업 2시간 전 배정 드라이버에게 텔레그램 알림 + 1시간 전 미확인 경고.

자세한 흐름은 blog/driver_reminder.py docstring 참고.

크론(15분 간격, 하루 종일 — 새벽 픽업도 있다):

    */15 * * * * .../python manage.py driver_pickup_reminder >> logs/driver_pickup_reminder.log 2>&1

TELEGRAM_DRIVER_BOT_TOKEN 이 비어 있으면 아무것도 하지 않는다.
"""

from django.core.management.base import BaseCommand

from blog.driver_reminder import ReminderRun
from utils import telegram_driver


class Command(BaseCommand):
    help = 'Telegram the assigned driver 2h before pickup; alert staff if not acknowledged by 1h before.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='발송/DB 기록 없이 대상과 메시지만 출력.')

    def handle(self, *args, **options):
        if not telegram_driver.is_configured() and not options['dry_run']:
            self.stdout.write('TELEGRAM_DRIVER_BOT_TOKEN not set — skipping.')
            return
        sent = ReminderRun(dry_run=options['dry_run'], stdout=self.stdout).run()
        self.stdout.write(f'Driver reminders sent: {sent}')
