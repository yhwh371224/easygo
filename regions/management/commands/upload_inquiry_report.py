import csv
import subprocess
from datetime import date, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from regions.models import RequestLog


class Command(BaseCommand):
    help = "Generate daily inquiry IP report and upload to Google Drive via rclone"

    REPORT_DIR = Path("/srv/inquiry_reports")
    GDRIVE_DEST = "gdrive:backup/easygo-inquiry/"
    KEEP_DAYS = 30

    def handle(self, *args, **options):
        self.REPORT_DIR.mkdir(parents=True, exist_ok=True)

        today = timezone.localdate()
        report_path = self.REPORT_DIR / f"inquiry_{today}.csv"

        logs = (
            RequestLog.objects.filter(created_at__date=today)
            .select_related("region")
            .order_by("created_at")
        )

        if not logs.exists():
            self.stdout.write(f"No inquiry logs for {today}, skipping.")
            return

        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        with open(report_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time", "ip", "email", "region", "path",
                "count_today", "count_week", "count_month",
                "flag_today", "flag_week", "flag_month",
            ])

            for log in logs:
                count_today = RequestLog.objects.filter(
                    ip=log.ip, created_at__date=today
                ).count()
                count_week = RequestLog.objects.filter(
                    ip=log.ip, created_at__date__gte=week_ago
                ).count()
                count_month = RequestLog.objects.filter(
                    ip=log.ip, created_at__date__gte=month_ago
                ).count()

                writer.writerow([
                    log.created_at.strftime("%H:%M:%S"),
                    log.ip,
                    log.email,
                    log.region.name if log.region else "",
                    log.path,
                    count_today,
                    count_week,
                    count_month,
                    "⚠️" if count_today >= 3 else "",
                    "⚠️" if count_week >= 3 else "",
                    "⚠️" if count_month >= 3 else "",
                ])

        self.stdout.write(f"✅ Report written: {report_path}")

        result = subprocess.run(
            ["rclone", "copy", str(report_path), self.GDRIVE_DEST],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            self.stdout.write(f"✅ Uploaded to {self.GDRIVE_DEST}")
        else:
            self.stderr.write(f"❌ rclone error: {result.stderr}")

        cutoff = today - timedelta(days=self.KEEP_DAYS)
        for old_file in self.REPORT_DIR.glob("inquiry_*.csv"):
            try:
                file_date = date.fromisoformat(old_file.stem.replace("inquiry_", ""))
                if file_date < cutoff:
                    old_file.unlink()
                    self.stdout.write(f"🗑️  Deleted old report: {old_file.name}")
            except ValueError:
                pass
