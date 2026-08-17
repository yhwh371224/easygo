import csv
import subprocess
from datetime import date, timedelta
from pathlib import Path

from django.db.models import Count
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from regions.models import RequestLog
from utils.telegram import send_telegram_sync


class Command(BaseCommand):
    help = "Generate daily inquiry IP report and upload to Google Drive via rclone"

    REPORT_DIR = Path("/srv/inquiry_reports")
    GDRIVE_DEST = "gdrive:backup/easygo-inquiry/"
    KEEP_DAYS = 30          # 로컬(/srv) 보관 일수
    GDRIVE_KEEP_DAYS = 90   # 원격(Drive) 보관 일수 — 서버 밖이라 더 오래 둔다

    def handle(self, *args, **options):
        # 실패는 전부 모아서 마지막에 CommandError 로 올린다 → 종료코드 1.
        # cronwrap 알림은 "마지막 출력"만 싣기 때문에, 트레이스백 대신 한 줄로
        # 원인이 보여야 크론 실패 메시지를 보고 바로 판단할 수 있다.
        errors = []

        try:
            self.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CommandError(f"리포트 디렉터리를 만들 수 없음 {self.REPORT_DIR}: {e}")

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

        flagged_ips = {
            ip for ip, cnt in today_counts.items() if cnt >= 3
        } | {
            ip for ip, cnt in week_counts.items() if cnt >= 3
        } | {
            ip for ip, cnt in month_counts.items() if cnt >= 3
        }

        if not flagged_ips:
            self.stdout.write(f"No flagged IPs for {today}, skipping.")
            return

        flagged = {}  # ip -> {email, count_today, count_week, count_month}

        with open(report_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time", "ip", "email", "region", "path",
                "count_today", "count_week", "count_month",
                "flag_today", "flag_week", "flag_month",
            ])

            for log in logs:
                if log.ip not in flagged_ips:
                    continue

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

                if log.ip not in flagged:
                    flagged[log.ip] = {
                        "email": log.email,
                        "count_today": count_today,
                        "count_week": count_week,
                        "count_month": count_month,
                    }

        # 플래그된 IP가 오늘 활동을 안 한 날은 헤더만 있는 CSV가 남는다.
        # 그런 빈 리포트까지 Drive 에 올리면 조용한 날마다 1줄짜리 파일이 쌓이므로
        # 로컬 파일을 지우고 업로드를 건너뛴다.
        upload_ok = True
        if not flagged:
            report_path.unlink(missing_ok=True)
            self.stdout.write(
                f"No flagged activity for {today} (empty report), nothing uploaded.")
        else:
            self.stdout.write(f"✅ Report written: {report_path}")

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
                errors.append(f"Telegram 전송 실패: {e}")

            result = subprocess.run(
                ["rclone", "copy", str(report_path), self.GDRIVE_DEST],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                self.stdout.write(f"✅ Uploaded to {self.GDRIVE_DEST}")
            else:
                upload_ok = False
                errors.append(f"rclone copy 실패: {result.stderr.strip()}")

        cutoff = today - timedelta(days=self.KEEP_DAYS)
        for old_file in self.REPORT_DIR.glob("inquiry_*.csv"):
            try:
                file_date = date.fromisoformat(old_file.stem.replace("inquiry_", ""))
                if file_date < cutoff:
                    old_file.unlink()
                    self.stdout.write(f"🗑️  Deleted old report: {old_file.name}")
            except ValueError:
                pass

        # 원격(Drive)도 정리하지 않으면 무한히 쌓인다. backup.sh 와 같은 방침으로
        # 원격은 로컬보다 오래 보관하고, 업로드가 실패한 실행에서는 건너뛴다
        # (rclone/네트워크가 깨진 상태에서 삭제만 하는 사고를 막는다).
        if not upload_ok:
            self.stderr.write("⚠️  업로드 실패 → 원격 정리 건너뜀")
        else:
            result = subprocess.run(
                ["rclone", "delete", "--min-age", f"{self.GDRIVE_KEEP_DAYS}d",
                 self.GDRIVE_DEST],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                self.stdout.write(
                    f"✅ Drive 정리 완료 ({self.GDRIVE_KEEP_DAYS}일 초과분)")
            else:
                errors.append(f"rclone delete 실패: {result.stderr.strip()}")

        if errors:
            raise CommandError(" | ".join(errors))
