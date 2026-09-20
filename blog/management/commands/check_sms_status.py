import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

# logs/sms.log 의 "[SMS SENT] to=... sid=..." 형식에서만 sid 를 추출할 수 있다
# (send_sms.py / send_arrivals.py 는 sid 를 로그에 남기지 않으므로 --recent 로는 못 찾는다).
SID_LOG_PATTERN = re.compile(r"\[SMS SENT\] to=(?P<to>\S+) sid=(?P<sid>SM\w+)")


class Command(BaseCommand):
    help = (
        "Twilio 로 보낸 SMS 의 실제 배달 상태(delivered/failed/undelivered 등)를 조회한다. "
        "SID 를 직접 지정하거나, --recent 로 logs/sms.log 에서 최근 발송분을 자동으로 찾아 확인한다."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "sids", nargs="*", help="조회할 Twilio message SID (SMxxxxxxxx...). 여러 개 지정 가능."
        )
        parser.add_argument(
            "--recent",
            type=int,
            default=None,
            metavar="N",
            help="SID 를 직접 주는 대신, logs/sms.log 에서 가장 최근 SMS SENT 로그 N건을 찾아 확인한다. "
            "(아무 인자 없이 실행하면 기본값 3건)",
        )

    def handle(self, *args, **options):
        sids = options["sids"]
        recent = options["recent"]

        if not sids and not recent:
            recent = 3  # 아무 인자 없이 실행하면 최근 3건을 보여준다

        entries = []  # list of (sid, to) — to 는 없으면 None
        if recent:
            entries = self._read_recent_from_log(recent)
            if not entries:
                self.stdout.write(self.style.WARNING("logs/sms.log 에서 SID 를 찾지 못했습니다."))
                return
        else:
            entries = [(sid, None) for sid in sids]

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        for sid, to in entries:
            self._check_one(client, sid, to)

    def _read_recent_from_log(self, n):
        log_path = os.path.join(settings.BASE_DIR, "logs/sms.log")
        if not os.path.exists(log_path):
            self.stderr.write(self.style.ERROR(f"로그 파일이 없습니다: {log_path}"))
            return []

        matches = []
        with open(log_path, "r", errors="ignore") as f:
            for line in f:
                m = SID_LOG_PATTERN.search(line)
                if m:
                    matches.append((m.group("sid"), m.group("to")))

        return matches[-n:]

    def _check_one(self, client, sid, to):
        try:
            message = client.messages(sid).fetch()
        except TwilioRestException as e:
            self.stdout.write(
                self.style.ERROR(f"[조회 실패] sid={sid} code={e.code} msg={e.msg}")
            )
            return

        status = message.status  # queued/sent/delivered/undelivered/failed 등
        to_display = to or message.to

        if status == "delivered":
            style = self.style.SUCCESS
        elif status in ("failed", "undelivered"):
            style = self.style.ERROR
        else:
            style = self.style.WARNING

        line = f"sid={sid} to={to_display} status={status}"
        if message.error_code:
            line += f" error_code={message.error_code} error_message={message.error_message}"

        self.stdout.write(style(line))
