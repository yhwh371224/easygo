#!/usr/bin/env bash
#
# EasyGo — cron 에서 Django management command 를 안전하게 실행하는 공용 러너.
#
#   scripts/cron/run.sh <command> [args...]
#
# · 스크립트 자기 위치로 프로젝트 루트를 찾으므로 서버마다 경로가 달라도 그대로 동작한다.
# · flock 으로 같은 커맨드가 겹쳐 도는 것을 막는다(앞 실행이 길어져도 중복 발송 없음).
# · 로그는 logs/cron/<command>.log 에 시각·종료코드와 함께 쌓이고, 커지면 1회 회전.
# · 실패했을 때만 stderr 로 한 줄 내보낸다 → crontab 의 MAILTO 로 실패 알림이 간다.
#   (정상 실행은 조용히 지나가므로 매시간 메일이 오지 않는다)

set -uo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <manage.py command> [args...]" >&2
    exit 2
fi

COMMAND="$1"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="$PROJECT_ROOT/venv/bin/python"
LOG_DIR="$PROJECT_ROOT/logs/cron"
LOG_FILE="$LOG_DIR/$COMMAND.log"
LOCK_FILE="/tmp/easygo-cron-$COMMAND.lock"
MAX_LOG_BYTES=$((10 * 1024 * 1024))   # 10MB 넘으면 .1 로 회전

ts() { date '+%Y-%m-%d %H:%M:%S %Z'; }

mkdir -p "$LOG_DIR" || exit 1

if [ ! -x "$PYTHON" ]; then
    echo "[$(ts)] FATAL: venv python 없음 → $PYTHON" >> "$LOG_FILE"
    echo "easygo cron: venv python 없음 ($PYTHON)" >&2
    exit 127
fi

# 로그 회전 — logrotate 설정 없이 자체 처리(직전 1개만 보관).
if [ -f "$LOG_FILE" ]; then
    SIZE="$(stat -c %s "$LOG_FILE" 2>/dev/null || echo 0)"
    if [ "$SIZE" -gt "$MAX_LOG_BYTES" ]; then
        mv -f "$LOG_FILE" "$LOG_FILE.1"
    fi
fi

cd "$PROJECT_ROOT" || exit 1

# 잠금은 fd 9 로 잡는다 — flock 자체의 실패(=이미 실행 중)와
# 커맨드의 실패를 종료코드로 구분하기 위해서.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "[$(ts)] ⏭ $COMMAND 건너뜀 — 이전 실행이 아직 돌고 있음" >> "$LOG_FILE"
    exit 0
fi

echo "[$(ts)] ▶ $COMMAND $*" >> "$LOG_FILE"

"$PYTHON" manage.py "$COMMAND" "$@" >> "$LOG_FILE" 2>&1
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
    echo "[$(ts)] ✔ $COMMAND 완료" >> "$LOG_FILE"
else
    echo "[$(ts)] ✘ $COMMAND 실패 (exit $STATUS)" >> "$LOG_FILE"
    echo "easygo cron: '$COMMAND' 실패 (exit $STATUS) — $LOG_FILE 확인" >&2
fi

exit "$STATUS"
