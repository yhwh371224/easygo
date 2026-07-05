import logging

from django.core.management.base import BaseCommand

from blog.models import Driver, DriverAgreement, CURRENT_AGREEMENT_VERSION
from utils.telegram import send_telegram_sync

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'List active drivers who have not confirmed the current subcontractor '
        'agreement version, and send a Telegram alert.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--agreement-version',
            dest='agreement_version',
            type=str,
            default=CURRENT_AGREEMENT_VERSION,
            help='Agreement version to check (default: current).',
        )

    def handle(self, *args, **options):
        version = options['agreement_version']

        confirmed_driver_ids = set(
            DriverAgreement.objects
            .filter(version=version, confirmed_at__isnull=False)
            .values_list('driver_id', flat=True)
        )

        unconfirmed = (
            Driver.objects
            .filter(is_active=True)
            .exclude(id__in=confirmed_driver_ids)
            .order_by('order')
        )

        count = unconfirmed.count()
        if not count:
            self.stdout.write(self.style.SUCCESS(
                f'All active drivers have confirmed agreement {version}.'
            ))
            return

        lines = [f"⚠️ {count} active driver(s) have not confirmed agreement {version}:"]
        for driver in unconfirmed:
            lines.append(f"• {driver.driver_name}")
        # Drivers confirm by logging into the portal → /driver/agreement/
        lines.append("→ Ask them to log in and confirm at /driver/agreement/")

        message = "\n".join(lines)
        self.stdout.write(message)

        try:
            send_telegram_sync(message)
        except Exception as e:
            logger.error(f"[check_unconfirmed_agreements] Telegram alert failed: {e}")
            self.stderr.write(self.style.ERROR(f'Telegram alert failed: {e}'))
