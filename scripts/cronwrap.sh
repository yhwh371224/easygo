#!/usr/bin/env bash
#
# 크론 작업을 감싸서, 실패한 실행만 골라 텔레그램으로 알린다.
#
# 크론이 보내는 메일은 아무도 읽지 않고 스크립트 실패는 로그에만 남아서,
# 자격증명 만료처럼 조용히 전건이 무너지는 장애를 며칠씩 모르고 지나간다.
# (2026-08-16 앱 비밀번호 폐기 건)
#
# utils/command_alerts.py 의 TelegramAlertMixin 과 역할이 다르다.
# 저쪽은 "커맨드는 떴는데 개별 건이 실패" 를 알리고, 이쪽은 "커맨드가 아예
# 안 떴다" 를 알린다. 그래서 Django 를 부르지 않고 curl 로만 보낸다 —
# venv 나 settings 가 깨진 게 실패 원인일 때도 알림은 나가야 하니까.
#
# 사용법:
#   cronwrap.sh /home/horeb/booking_reminder.sh
#   cronwrap.sh -n clearsessions -- bash -c 'cd /path && venv/bin/python manage.py clearsessions'
#   cronwrap.sh -t 1800 /home/horeb/dumpdata.sh          # 30분 넘으면 죽이고 알림
#   cronwrap.sh -p 'Traceback' /home/horeb/watch_gmail.sh # 출력에 패턴이 있으면 실패 취급
#
# 옵션:
#   -n NAME      알림/로그에 쓸 이름 (기본: 명령 파일명에서 .sh 제거)
#   -t SECONDS   타임아웃. 초과하면 강제 종료 후 실패로 알린다
#   -p REGEX     종료코드가 0이어도 출력이 이 패턴과 맞으면 실패로 본다
#   -l LOGFILE   로그를 이 파일에 남긴다. 원래 크론 줄에 `>> 로그 2>&1` 이
#                붙어 있던 작업용 — 리다이렉트를 떼고 이 옵션으로 넘기면
#                로그 위치는 그대로 두면서 출력이 알림에도 실린다.
#                (이 경우 자동 잘라내기는 하지 않는다. 남의 로테이션 정책이므로)
#
# 환경변수:
#   CRONWRAP_ENV        .env 경로            (기본: /home/horeb/github/easygo/.env)
#   CRONWRAP_LOG_DIR    실행 로그 디렉터리   (기본: /home/horeb/logs/cron)
#   CRONWRAP_MIN_GAP    같은 작업 재알림 최소 간격(초). 0이면 매번 (기본: 3600)

set -uo pipefail

ENV_FILE="${CRONWRAP_ENV:-/home/horeb/github/easygo/.env}"
LOG_DIR="${CRONWRAP_LOG_DIR:-/home/horeb/logs/cron}"
STATE_DIR="$LOG_DIR/.state"
MIN_GAP="${CRONWRAP_MIN_GAP:-3600}"
MAX_LOG_BYTES=$((5 * 1024 * 1024))

NAME=""
TIMEOUT=""
FAIL_PATTERN=""
CUSTOM_LOG=""

while getopts ":n:t:p:l:" opt; do
    case "$opt" in
        n) NAME="$OPTARG" ;;
        t) TIMEOUT="$OPTARG" ;;
        p) FAIL_PATTERN="$OPTARG" ;;
        l) CUSTOM_LOG="$OPTARG" ;;
        *) echo "cronwrap: 알 수 없는 옵션 -$OPTARG" >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))
[ "${1:-}" = "--" ] && shift

if [ $# -eq 0 ]; then
    echo "사용법: cronwrap.sh [-n 이름] [-t 초] [-p 패턴] 명령 [인자...]" >&2
    exit 2
fi

if [ -z "$NAME" ]; then
    NAME="$(basename "$1")"
    NAME="${NAME%.sh}"
fi
SAFE_NAME="$(printf '%s' "$NAME" | tr -c 'A-Za-z0-9_.-' '_')"

mkdir -p "$LOG_DIR" "$STATE_DIR" 2>/dev/null
STATE_FILE="$STATE_DIR/$SAFE_NAME"
if [ -n "$CUSTOM_LOG" ]; then
    LOG_FILE="$CUSTOM_LOG"
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null
else
    LOG_FILE="$LOG_DIR/$SAFE_NAME.log"
fi

# .env 에서 값 하나를 읽는다. 주석(#로 시작)은 앵커에 걸려 자동으로 빠지고,
# 같은 키가 여러 번 나오면 마지막 값을 쓴다 — python-decouple 이 뒤엣것으로
# 덮어쓰므로 Django 가 실제로 쓰는 값과 어긋나지 않게 맞춘 것이다.
read_env() {
    [ -r "$ENV_FILE" ] || return 1
    sed -nE "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$ENV_FILE" \
        | tail -n1 \
        | sed -E 's/[[:space:]]+$//; s/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/'
}

notify() {
    local text="$1"
    local token chat_id
    token="$(read_env TELEGRAM_BOT_TOKEN)"
    chat_id="$(read_env TELEGRAM_CHAT_ID)"

    if [ -z "$token" ] || [ -z "$chat_id" ]; then
        echo "[cronwrap] 텔레그램 자격증명을 못 읽음: $ENV_FILE" >&2
        return 1
    fi

    # parse_mode 를 쓰지 않는다. 스택트레이스에 _ * [ 가 섞이면 텔레그램이
    # 400 으로 거절하는데, 하필 그게 제일 알아야 할 알림이다.
    local http
    http="$(curl -sS -o /dev/null -w '%{http_code}' \
        --max-time 15 --retry 2 --retry-delay 3 \
        "https://api.telegram.org/bot$token/sendMessage" \
        --data-urlencode "chat_id=$chat_id" \
        --data-urlencode "text=$text" 2>&1)"

    if [ "$http" != "200" ]; then
        echo "[cronwrap] 텔레그램 전송 실패 (HTTP $http)" >&2
        return 1
    fi
}

OUT_FILE="$(mktemp "/tmp/cronwrap.$SAFE_NAME.XXXXXX")"
trap 'rm -f "$OUT_FILE"' EXIT

START_TS="$(date +%s)"
STARTED_AT="$(date '+%Y-%m-%d %H:%M:%S')"

if [ -n "$TIMEOUT" ]; then
    timeout -k 30 "$TIMEOUT" "$@" >"$OUT_FILE" 2>&1
else
    "$@" >"$OUT_FILE" 2>&1
fi
STATUS=$?

ELAPSED=$(( $(date +%s) - START_TS ))

REASON=""
if [ "$STATUS" -ne 0 ]; then
    if [ -n "$TIMEOUT" ] && { [ "$STATUS" -eq 124 ] || [ "$STATUS" -eq 137 ]; }; then
        REASON="타임아웃 ${TIMEOUT}초 초과로 강제 종료"
    else
        REASON="종료코드 $STATUS"
    fi
elif [ -n "$FAIL_PATTERN" ] && grep -qE "$FAIL_PATTERN" "$OUT_FILE"; then
    REASON="종료코드는 0이지만 출력이 실패 패턴과 일치: $FAIL_PATTERN"
    STATUS=1
fi

{
    echo "===== $STARTED_AT | $NAME | ${ELAPSED}s | exit=$STATUS ====="
    cat "$OUT_FILE"
} >>"$LOG_FILE" 2>/dev/null

# 로그가 무한정 자라지 않게 한 번씩 잘라낸다. cleanup_logs.sh 손 안 대도 되게.
# -l 로 기존 로그 파일을 지정한 경우는 건드리지 않는다 — 그쪽 로테이션이 따로 있다.
LOG_SIZE=0
[ -z "$CUSTOM_LOG" ] && LOG_SIZE="$(wc -c <"$LOG_FILE" 2>/dev/null || echo 0)"
if [ "$LOG_SIZE" -gt "$MAX_LOG_BYTES" ]; then
    tail -n 2000 "$LOG_FILE" >"$LOG_FILE.tmp" 2>/dev/null && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

# 이전 실행 상태: "연속실패횟수 마지막알림시각 억제된횟수"
PREV_FAILS=0; LAST_ALERT=0; SUPPRESSED=0
if [ -r "$STATE_FILE" ]; then
    read -r PREV_FAILS LAST_ALERT SUPPRESSED <"$STATE_FILE" 2>/dev/null
    PREV_FAILS="${PREV_FAILS:-0}"; LAST_ALERT="${LAST_ALERT:-0}"; SUPPRESSED="${SUPPRESSED:-0}"
fi

NOW="$(date +%s)"
HOST="$(hostname -s 2>/dev/null || echo unknown)"

if [ "$STATUS" -eq 0 ]; then
    # 계속 실패하다가 살아났으면 그것도 알려야 한다. 알림만 끊기고 실제로는
    # 안 고쳐진 상태인지, 진짜 복구된 건지 구분이 안 되면 알림을 못 믿게 된다.
    if [ "$PREV_FAILS" -gt 0 ]; then
        notify "✅ 크론 복구: $NAME
서버: $HOST
시각: $STARTED_AT (${ELAPSED}s)
직전까지 ${PREV_FAILS}회 연속 실패했습니다."
    fi
    printf '0 0 0\n' >"$STATE_FILE"
    exit 0
fi

FAILS=$(( PREV_FAILS + 1 ))

# 30분마다 도는 작업이 계속 깨지면 하루에 48통이 온다. 그렇게 되면 사람은
# 알림 자체를 무시한다. 첫 실패는 즉시 보내고, 이후 반복은 간격을 둔 뒤
# "그동안 몇 번 더 실패했는지" 를 묶어서 알린다.
if [ "$MIN_GAP" -gt 0 ] && [ "$FAILS" -gt 1 ] && [ $(( NOW - LAST_ALERT )) -lt "$MIN_GAP" ]; then
    printf '%s %s %s\n' "$FAILS" "$LAST_ALERT" "$(( SUPPRESSED + 1 ))" >"$STATE_FILE"
    exit "$STATUS"
fi

TAIL_OUT="$(tail -c 1200 "$OUT_FILE" | tail -n 25)"
if [ -z "${TAIL_OUT//[[:space:]]/}" ]; then
    TAIL_OUT="(출력 없음 — 스크립트가 내부에서 로그로 리다이렉트했을 수 있습니다)"
fi

REPEAT=""
if [ "$FAILS" -gt 1 ]; then
    REPEAT="
연속 실패: ${FAILS}회"
    [ "$SUPPRESSED" -gt 0 ] && REPEAT="$REPEAT (직전 알림 이후 ${SUPPRESSED}회는 묶어서 생략)"
fi

notify "🚨 크론 실패: $NAME
서버: $HOST
시각: $STARTED_AT (${ELAPSED}s)
원인: $REASON$REPEAT
명령: $*
로그: $LOG_FILE

--- 마지막 출력 ---
$TAIL_OUT"

printf '%s %s 0\n' "$FAILS" "$NOW" >"$STATE_FILE"
exit "$STATUS"
