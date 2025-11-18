from django.core.management.base import BaseCommand
from monitor.fred_monitor import check_and_alert


class Command(BaseCommand):
    help = "Send liquidity monitor summary email (all 4 indicators)"

    def handle(self, *args, **kwargs):
        check_and_alert()
        self.stdout.write(self.style.SUCCESS("Liquidity email sent successfully."))

