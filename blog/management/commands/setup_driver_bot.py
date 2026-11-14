"""드라이버 봇 webhook 등록. 토큰/시크릿을 .env 에 넣고 배포한 뒤 운영 서버에서 한 번 실행.

    python manage.py setup_driver_bot           # webhook 등록 + 봇 정보 출력
    python manage.py setup_driver_bot --info    # 현재 webhook 상태만 확인
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from utils import telegram_driver


class Command(BaseCommand):
    help = 'Register the driver Telegram bot webhook.'

    def add_arguments(self, parser):
        parser.add_argument('--info', action='store_true', help='현재 webhook 상태만 출력.')

    def handle(self, *args, **options):
        if not telegram_driver.is_configured():
            raise CommandError('TELEGRAM_DRIVER_BOT_TOKEN is not set.')
        me = telegram_driver.call('getMe')
        self.stdout.write(f"Bot: @{me.get('username')} ({me.get('first_name')})")
        configured = (settings.TELEGRAM_DRIVER_BOT_USERNAME or '').lstrip('@')
        if configured != me.get('username'):
            self.stdout.write(self.style.WARNING(
                f"TELEGRAM_DRIVER_BOT_USERNAME is '{configured}' — set it to "
                f"'{me.get('username')}' or the dashboard Connect button stays hidden/wrong."
            ))

        if not options['info']:
            secret = settings.TELEGRAM_DRIVER_WEBHOOK_SECRET
            if not secret:
                raise CommandError('TELEGRAM_DRIVER_WEBHOOK_SECRET is not set.')
            url = settings.SITE_URL.rstrip('/') + reverse('telegram_driver_webhook')
            telegram_driver.call(
                'setWebhook', url=url, secret_token=secret,
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Webhook set: {url}'))

        info = telegram_driver.call('getWebhookInfo')
        self.stdout.write(
            f"url={info.get('url')} pending={info.get('pending_update_count')} "
            f"last_error={info.get('last_error_message') or '-'}"
        )
