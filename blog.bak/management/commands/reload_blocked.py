# yourapp/management/commands/reload_blocked.py
from django.core.management.base import BaseCommand
from main.middlewares.block_ip_middleware import BlockIPEmailMiddleware


class Command(BaseCommand):
    help = "Reload blocked IPs and emails from files"

    def handle(self, *args, **kwargs):
        mw = BlockIPEmailMiddleware(lambda r: r)
        mw.load_blocked_lists()
        self.stdout.write(self.style.SUCCESS("✅ Blocked IP and email lists reloaded successfully."))
