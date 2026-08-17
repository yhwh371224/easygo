"""upload_inquiry_report 의 업로드/정리 분기 테스트.

이 커맨드는 2026-05-19 배포 후 3개월간 /srv 권한 문제로 한 번도 돌지 않았다.
빈 리포트 업로드 스킵과 원격 보관 정리는 크론에서만 드러나는 경로라 여기서 고정한다.
"""
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from regions.models import RequestLog


class FakeCompleted:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


class UploadInquiryReportTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def _run(self, report_dir, rclone_side_effect=None, telegram_side_effect=None):
        """커맨드를 실행한다. rclone 호출 기록은 예외가 나도 self.calls 에 남는다."""
        from regions.management.commands import upload_inquiry_report as mod

        self.calls = calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if rclone_side_effect:
                return rclone_side_effect(cmd)
            return FakeCompleted()

        with patch.object(mod.Command, "REPORT_DIR", Path(report_dir)), \
                patch.object(mod, 'subprocess') as sp, \
                patch.object(mod, 'send_telegram_sync') as tg:
            sp.run.side_effect = fake_run
            tg.side_effect = telegram_side_effect
            call_command('upload_inquiry_report')
        return calls, tg

    def _log(self, ip, days_ago=0, email='a@b.com'):
        log = RequestLog.objects.create(ip=ip, path='/inquiry/', email=email)
        if days_ago:
            RequestLog.objects.filter(pk=log.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago))
        return log

    def test_flagged_today_uploads_and_prunes_remote(self):
        for _ in range(3):
            self._log('1.1.1.1')

        calls, tg = self._run(self.tmp)

        today = timezone.localdate()
        report = Path(self.tmp) / f"inquiry_{today}.csv"
        self.assertTrue(report.exists(), "플래그 건이 있으면 리포트가 남아야 한다")
        self.assertGreater(len(report.read_text().splitlines()), 1,
                           "헤더 외에 데이터 행이 있어야 한다")
        tg.assert_called_once()
        self.assertEqual([c[1] for c in calls], ['copy', 'delete'],
                         "업로드 후 원격 정리까지 실행돼야 한다")
        self.assertIn('--min-age', calls[1])

    def test_empty_report_is_not_uploaded(self):
        """주간 기준으로만 플래그된 IP가 오늘 조용하면 빈 리포트가 나온다."""
        for _ in range(3):
            self._log('2.2.2.2', days_ago=3)
        self._log('9.9.9.9')  # 오늘 활동했지만 플래그 대상 아님

        calls, tg = self._run(self.tmp)

        today = timezone.localdate()
        report = Path(self.tmp) / f"inquiry_{today}.csv"
        self.assertFalse(report.exists(), "빈 리포트는 로컬에서 지워져야 한다")
        tg.assert_not_called()
        # 올릴 게 없어도 원격 보관 정리는 돈다 — 조용한 날이 이어질 때
        # 90일 초과분이 Drive 에 계속 남는 걸 막는다.
        self.assertEqual([c[1] for c in calls], ['delete'],
                         "업로드는 건너뛰되 원격 정리는 실행돼야 한다")

    def test_failed_upload_skips_remote_prune_and_raises(self):
        for _ in range(3):
            self._log('3.3.3.3')

        def fail_copy(cmd):
            return FakeCompleted(returncode=1, stderr='boom')

        with self.assertRaises(CommandError) as ctx:
            self._run(self.tmp, rclone_side_effect=fail_copy)

        self.assertIn('boom', str(ctx.exception))
        self.assertEqual([c[1] for c in self.calls], ['copy'],
                         "업로드가 실패하면 원격 삭제는 하지 않아야 한다")

    def test_failed_remote_prune_raises(self):
        for _ in range(3):
            self._log('4.4.4.4')

        def fail_delete(cmd):
            if cmd[1] == 'delete':
                return FakeCompleted(returncode=1, stderr='prune boom')
            return FakeCompleted()

        with self.assertRaises(CommandError) as ctx:
            self._run(self.tmp, rclone_side_effect=fail_delete)

        self.assertIn('prune boom', str(ctx.exception))

    def test_telegram_failure_still_uploads_then_raises(self):
        """알림이 실패해도 업로드·정리는 끝까지 하고, 그 다음에 실패로 끝난다."""
        for _ in range(3):
            self._log('5.5.5.5')

        with self.assertRaises(CommandError) as ctx:
            self._run(self.tmp, telegram_side_effect=RuntimeError('tg down'))

        self.assertIn('tg down', str(ctx.exception))
        self.assertEqual([c[1] for c in self.calls], ['copy', 'delete'],
                         "알림 실패가 업로드/정리를 막으면 안 된다")

    def test_unwritable_report_dir_raises_clean_error(self):
        """/srv 권한 문제(3개월 장애의 원인)는 트레이스백 대신 한 줄로 보고한다."""
        for _ in range(3):
            self._log('6.6.6.6')

        with self.assertRaises(CommandError) as ctx:
            self._run('/proc/nonexistent/inquiry_reports')

        self.assertIn('리포트 디렉터리를 만들 수 없음', str(ctx.exception))
