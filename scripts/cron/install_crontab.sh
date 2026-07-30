#!/usr/bin/env bash
#
# EasyGo 독촉 스케줄을 현재 사용자 crontab 에 "덧붙여" 설치한다.
#
#   scripts/cron/install_crontab.sh            # 설치 / 갱신
#   scripts/cron/install_crontab.sh --dry-run  # 설치될 결과만 출력
#   scripts/cron/install_crontab.sh --uninstall # 이 블록만 제거
#
# ⚠ `crontab <파일>` 은 기존 crontab 을 통째로 덮어쓴다. 실서버에는 이미 다른
#   EasyGo 작업(booking_reminder, assign_drivers 등)이 등록돼 있을 수 있으므로
#   이 스크립트는 절대 덮어쓰지 않는다. 아래 마커 블록만 찾아 교체하고,
#   나머지 줄은 순서 그대로 보존한다. 설치 전 백업도 남긴다.

set -uo pipefail

BEGIN_MARK='# >>> easygo dunning (managed by scripts/cron/install_crontab.sh) >>>'
END_MARK='# <<< easygo dunning <<<'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATE="$SCRIPT_DIR/easygo-dunning.crontab"
RUNNER="$SCRIPT_DIR/run.sh"
BACKUP_DIR="$PROJECT_ROOT/logs/cron"

MODE='install'
case "${1:-}" in
    --dry-run)   MODE='dry-run' ;;
    --uninstall) MODE='uninstall' ;;
    '')          ;;
    *)           echo "usage: $0 [--dry-run|--uninstall]" >&2; exit 2 ;;
esac

[ -f "$TEMPLATE" ] || { echo "템플릿 없음: $TEMPLATE" >&2; exit 1; }
[ -x "$RUNNER" ]   || { echo "러너에 실행권한 없음: $RUNNER  (chmod +x 필요)" >&2; exit 1; }

# 현재 crontab (없으면 빈 내용). "no crontab for user" 는 정상 상황이라 무시.
CURRENT="$(crontab -l 2>/dev/null)"

# 기존 관리 블록 제거 → 남은 줄이 보존 대상.
PRESERVED="$(printf '%s\n' "$CURRENT" | awk -v b="$BEGIN_MARK" -v e="$END_MARK" '
    $0 == b { skip = 1; next }
    $0 == e { skip = 0; next }
    !skip   { print }
')"
# 블록 제거로 생긴 끝쪽 빈 줄 정리.
PRESERVED="$(printf '%s\n' "$PRESERVED" | sed -e :a -e '/^\n*$/{$d;N;};/\n$/ba')"

# 관리 블록 밖에 같은 커맨드가 이미 걸려 있으면 이중 스케줄이 된다.
# (실서버에는 예전에 손으로 넣은 줄이 있을 수 있다 — 각 단계는 *_sent_at 로
#  중복 발송이 막히지만, 스케줄이 둘이면 나중에 시각을 바꿀 때 헷갈린다)
# 주석 줄은 먼저 걸러낸다 — grep -n 이 줄번호를 앞에 붙이므로 번호까지 감안해 지운다.
DUPES="$(printf '%s\n' "$PRESERVED" \
    | grep -nE 'no_payment_yet|auto_cancel_pending|final_notice|send_final_warning' \
    | grep -vE '^[0-9]+:[[:space:]]*#')"
if [ -n "$DUPES" ]; then
    echo "⚠ 관리 블록 밖에 같은 커맨드가 이미 등록돼 있습니다 — 이중 실행 가능:" >&2
    printf '%s\n' "$DUPES" | sed 's/^/    /' >&2
    echo "  → 위 줄들을 지운 뒤 다시 실행하거나, 이 블록 설치를 건너뛰세요." >&2
    echo >&2
fi

if [ "$MODE" = 'uninstall' ]; then
    printf '%s\n' "$PRESERVED" | crontab - || exit 1
    echo "제거 완료 — easygo dunning 블록을 crontab 에서 뺐습니다."
    exit 0
fi

BLOCK="$(sed "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" "$TEMPLATE")"
NEW_CRONTAB="$(printf '%s\n\n%s\n%s\n%s\n' "$PRESERVED" "$BEGIN_MARK" "$BLOCK" "$END_MARK")"

if [ "$MODE" = 'dry-run' ]; then
    echo "===== 설치될 crontab 전체 (실제 반영 안 함) ====="
    printf '%s\n' "$NEW_CRONTAB"
    exit 0
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/crontab.backup.$(date '+%Y%m%d-%H%M%S')"
printf '%s\n' "$CURRENT" > "$BACKUP_FILE"

if ! printf '%s\n' "$NEW_CRONTAB" | crontab -; then
    echo "설치 실패 — 기존 crontab 그대로입니다. 백업: $BACKUP_FILE" >&2
    exit 1
fi

echo "설치 완료."
echo "  백업     : $BACKUP_FILE   (되돌리려면: crontab \"$BACKUP_FILE\")"
echo "  프로젝트 : $PROJECT_ROOT"
echo "  로그     : $PROJECT_ROOT/logs/cron/"
echo
echo "현재 등록된 easygo 작업:"
crontab -l | grep -F 'scripts/cron/run.sh' | sed 's/^/  /'
