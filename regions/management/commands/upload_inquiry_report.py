import csv
import subprocess
from datetime import date, timedelta
from pathlib import Path

from django.db.models import Count
from django.core.management.base import BaseCommand
from django.utils import timezone

from regions.models import RequestLog
from utils.telegram import send_telegram_sync


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

        def _ip_counts(qs):
            return {
                row['ip']: row['cnt']
                for row in qs.values('ip').annotate(cnt=Count('ip'))
            }

        today_counts = _ip_counts(RequestLog.objects.filter(created_at__date=today))
        week_counts  = _ip_counts(RequestLog.objects.filter(created_at__date__gte=week_ago))
        month_counts = _ip_counts(RequestLog.objects.filter(created_at__date__gte=month_ago))

        flagged = {}  # ip -> {email, count_today, count_week, count_month}

        with open(report_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time", "ip", "email", "region", "path",
                "count_today", "count_week", "count_month",
                "flag_today", "flag_week", "flag_month",
            ])

            for log in logs:
                count_today = today_counts.get(log.ip, 0)
                count_week  = week_counts.get(log.ip, 0)
                count_month = month_counts.get(log.ip, 0)

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

                if count_today >= 3 or count_week >= 3 or count_month >= 3:
                    if log.ip not in flagged:
                        flagged[log.ip] = {
                            "email": log.email,
                            "count_today": count_today,
                            "count_week": count_week,
                            "count_month": count_month,
                        }

        self.stdout.write(f"✅ Report written: {report_path}")

        if flagged:
            lines = [f"⚠️ *Inquiry Flag Report* — {today}\n"]
            for ip, info in flagged.items():
                flags = []
                if info["count_today"] >= 3:
                    flags.append(f"오늘 {info['count_today']}회")
                if info["count_week"] >= 3:
                    flags.append(f"주간 {info['count_week']}회")
                if info["count_month"] >= 3:
                    flags.append(f"월간 {info['count_month']}회")
                lines.append(f"• `{ip}` ({info['email']}) — {', '.join(flags)}")
            lines.append(f"\n총 {len(flagged)}개 IP 플래그")
            try:
                send_telegram_sync("\n".join(lines))
                self.stdout.write(f"✅ Telegram 알림 전송: {len(flagged)}개 IP")
            except Exception as e:
                self.stderr.write(f"❌ Telegram 전송 실패: {e}")

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
