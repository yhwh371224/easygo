"""관리 커맨드의 실패를 모아 텔레그램 한 통으로 알린다.

크론으로 도는 발송 커맨드는 실패해도 로그에만 남아서, 자격증명 만료처럼 조용히
전건이 무너지는 장애를 며칠씩 모르고 지나갈 수 있다(2026-08-16 앱 비밀번호 폐기 건).

건당 알림이 아니라 실행당 한 통인 이유: 그런 전면 장애에서는 대상 예약 수만큼
알림이 쏟아져 오히려 알림을 무시하게 된다. 넘치면 잘라내고 로그로 넘긴다.
"""

import logging

from utils.telegram import send_telegram_sync

logger = logging.getLogger(__name__)

MAX_ALERT_LINES = 10


class TelegramAlertMixin:
    """BaseCommand 앞에 섞어 쓴다 — `class Command(TelegramAlertMixin, BaseCommand)`.

    커맨드가 `self.alerts.append(...)` 로 실패를 쌓아두면 실행이 끝날 때
    (예외로 죽더라도) 자동으로 한 통 보낸다.
    """

    # 지정하면 첫 줄에 "⚠️ {alert_header} {건수}건" 이 붙는다. 실패만 담는
    # 커맨드용. 지연·미배정 같은 비실패 알림이 섞이는 커맨드는 비워 둔다.
    alert_header = None

    @property
    def alerts(self):
        if not hasattr(self, '_alerts'):
            self._alerts = []
        return self._alerts

    def execute(self, *args, **options):
        # handle() 안에서 flush 를 부르면 커맨드가 중간에 죽었을 때 이미 쌓인
        # 알림까지 같이 사라진다. 죽는 경우가 제일 알아야 할 경우라 여기서 감싼다.
        try:
            return super().execute(*args, **options)
        except Exception as e:
            self.alerts.append(f"💥 커맨드 중단 | {type(e).__name__}: {str(e)[:200]}")
            raise
        finally:
            self.flush_alerts()

    def flush_alerts(self):
        if not self.alerts:
            return

        label = self.alert_header or type(self).__module__.rsplit('.', 1)[-1]
        lines = self.alerts[:MAX_ALERT_LINES]
        if len(self.alerts) > MAX_ALERT_LINES:
            lines.append(f"…외 {len(self.alerts) - MAX_ALERT_LINES}건 (logs/django.log 참조)")
        if self.alert_header:
            lines.insert(0, f"⚠️ {self.alert_header} {len(self.alerts)}건")

        try:
            send_telegram_sync('\n'.join(lines))
        except Exception as e:
            logger.error('[%s] 텔레그램 알림 전송 실패: %s', label, e)
        finally:
            # 같은 프로세스에서 두 번 호출돼도 중복 발송되지 않게 비운다.
            self._alerts = []
