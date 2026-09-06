#!/bin/bash
# ============================================================================
# compact_payment_fees.sh — monthly PayPal/Stripe fee compaction, self-checked
#
# 1. Independently sums PayPal/Stripe rows straight from the
#    accounting_paymentfeelog table via psql (bypasses Django/ORM entirely —
#    a true cross-check against the same table compact_payment_fees reads).
# 2. Runs `manage.py compact_payment_fees --dry-run` for the same month.
# 3. If the two agree exactly -> applies automatically, no prompt (safe for
#    unattended cron).
# 4. If they disagree at all -> does NOT apply, sends a Telegram + email
#    alert (reusing utils.telegram.send_telegram_sync / utils.email.send_text_email,
#    the same channels basecamp/tasks.py already uses for fee-recording
#    failures) and exits non-zero.
#
# Usage:
#   ./compact_payment_fees.sh           # previous calendar month (cron use)
#   ./compact_payment_fees.sh 2026-07   # explicit month (manual/testing)
#
# Place at: /home/horeb/compact_payment_fees.sh  (chmod +x)
# Cron (7th of month, 06:00, previous month's data):
#   0 6 7 * * /home/horeb/compact_payment_fees.sh >> /home/horeb/logs/compact_payment_fees.log 2>&1
# ============================================================================
set -euo pipefail

export PATH="/home/horeb/github/easygo/venv/bin:/usr/local/bin:/usr/bin:/bin"
PROJECT_DIR="/home/horeb/github/easygo"
cd "$PROJECT_DIR" || exit 1
source venv/bin/activate

# --- target month ------------------------------------------------------
if [ -n "${1:-}" ]; then
    TARGET_MONTH="$1"
else
    TARGET_MONTH=$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m)
fi
MONTH_START="${TARGET_MONTH}-01"
MONTH_END=$(date -d "$MONTH_START +1 month -1 day" +%Y-%m-%d)

echo "============================================================"
echo " $(date '+%F %T')  Target month: $TARGET_MONTH  ($MONTH_START ~ $MONTH_END)"
echo "============================================================"

# --- DB credentials straight from .env (same values Django reads) ------
# .env has a legacy mysql block ahead of the current postgres block, so some
# keys (e.g. DB_HOST) appear twice — take the last match, matching how
# python-dotenv resolves duplicate keys.
DB_NAME=$(grep -E '^DB_NAME='     .env | tail -1 | cut -d= -f2-)
DB_USER=$(grep -E '^DB_USER='     .env | tail -1 | cut -d= -f2-)
DB_PASSWORD=$(grep -E '^DB_PASSWORD=' .env | tail -1 | cut -d= -f2-)
DB_HOST=$(grep -E '^DB_HOST='     .env | tail -1 | cut -d= -f2- || echo "localhost")
DB_PORT=$(grep -E '^DB_PORT='     .env | tail -1 | cut -d= -f2- || echo "5432")
export PGPASSWORD="$DB_PASSWORD"

# --- independent sum, straight from Postgres (no Django involved) ------
# Reads accounting_paymentfeelog directly — the same table
# accounting.models.PaymentFeeLog / compact_payment_fees reads through the
# ORM, so this is a true independent cross-check of that table's contents,
# not of accounting_transaction (individual fee rows are never written
# there — see accounting/models/payment_fee_log.py's docstring; before the
# 2026-08-24 switch to PaymentFeeLog they briefly were, which is why this
# used to query accounting_transaction and falsely flagged every month
# straddling that cutover).
independent_sum() {
    local source="$1"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' -c "
        SELECT COUNT(*),
               COALESCE(ROUND(SUM(gross_amount)::numeric, 2), 0),
               COALESCE(ROUND(SUM(gst_amount)::numeric, 2), 0)
        FROM accounting_paymentfeelog
        WHERE source = '${source}'
          AND date >= '${MONTH_START}'
          AND date <= '${MONTH_END}';
    "
}

read -r PP_COUNT PP_GROSS PP_GST <<< "$(independent_sum paypal | tr '|' ' ')"
read -r SP_COUNT SP_GROSS SP_GST <<< "$(independent_sum stripe | tr '|' ' ')"

echo ""
echo "--- Independent (psql) totals ---"
printf "  paypal : %s rows, gross=%s, gst=%s\n" "$PP_COUNT" "$PP_GROSS" "$PP_GST"
printf "  stripe : %s rows, gross=%s, gst=%s\n" "$SP_COUNT" "$SP_GROSS" "$SP_GST"

# --- dry-run from the Django management command -------------------------
echo ""
echo "--- manage.py compact_payment_fees --dry-run ---"
DRY_OUTPUT=$(python manage.py compact_payment_fees --month "$TARGET_MONTH" --dry-run)
echo "$DRY_OUTPUT"

parse_dry_run() {
    local source="$1" out="$2"
    local line count gross gst
    line=$(echo "$out" | grep "^${source}:" || true)
    if [[ "$line" == *"no rows"* || -z "$line" ]]; then
        echo "0|0.00|0.00"
        return
    fi
    count=$(echo "$line" | grep -oP '^\w+: \K[0-9]+')
    gross=$(echo "$line" | grep -oP 'gross=\K[0-9.]+')
    gst=$(echo "$line" | grep -oP 'gst=\K[0-9.]+')
    printf "%s|%.2f|%.2f\n" "$count" "$gross" "$gst"
}

read -r PP_D_COUNT PP_D_GROSS PP_D_GST <<< "$(parse_dry_run paypal "$DRY_OUTPUT" | tr '|' ' ')"
read -r SP_D_COUNT SP_D_GROSS SP_D_GST <<< "$(parse_dry_run stripe "$DRY_OUTPUT" | tr '|' ' ')"

# --- compare --------------------------------------------------------------
norm() { awk "BEGIN{printf \"%.2f\", $1}"; }

MISMATCH_DETAILS=""
for pair in \
    "paypal count $PP_COUNT $PP_D_COUNT" \
    "paypal gross $(norm "$PP_GROSS") $(norm "$PP_D_GROSS")" \
    "paypal gst   $(norm "$PP_GST") $(norm "$PP_D_GST")" \
    "stripe count $SP_COUNT $SP_D_COUNT" \
    "stripe gross $(norm "$SP_GROSS") $(norm "$SP_D_GROSS")" \
    "stripe gst   $(norm "$SP_GST") $(norm "$SP_D_GST")"
do
    read -r src field a b <<< "$pair"
    if [ "$a" != "$b" ]; then
        LINE="MISMATCH [$src $field]: psql=$a  dry-run=$b"
        echo "$LINE"
        MISMATCH_DETAILS="${MISMATCH_DETAILS}${LINE}"$'\n'
    fi
done

# --- mismatch: alert, do NOT apply ----------------------------------------
if [ -n "$MISMATCH_DETAILS" ]; then
    echo ""
    echo "!! 값이 서로 다릅니다. 적용하지 않고 종료합니다."
    export ALERT_MSG="[EasyGo] compact_payment_fees 검증 실패 ($TARGET_MONTH)

psql와 dry-run 결과가 일치하지 않아 자동 적용을 건너뛰었습니다.
수동으로 확인 후 적용해주세요.

$MISMATCH_DETAILS"
    python manage.py shell -c "
import os
from django.conf import settings
from utils.telegram import send_telegram_sync
from utils.email import send_text_email
msg = os.environ['ALERT_MSG']
send_telegram_sync(msg)
send_text_email('compact_payment_fees 검증 실패 ($TARGET_MONTH)', msg, [settings.RECIPIENT_EMAIL])
" || echo "!! 알림 전송 자체도 실패했습니다 — 로그를 직접 확인하세요."
    exit 1
fi

# --- nothing to do ----------------------------------------------------------
if [ "$PP_COUNT" = "0" ] && [ "$SP_COUNT" = "0" ]; then
    echo ""
    echo "압축할 row가 없습니다 ($TARGET_MONTH). 종료합니다."
    exit 0
fi

# --- match: apply automatically ---------------------------------------------
echo ""
echo "값이 일치합니다 (psql == dry-run). 자동 적용합니다."
if ! python manage.py compact_payment_fees --month "$TARGET_MONTH"; then
    export ALERT_MSG="[EasyGo] compact_payment_fees 실행 실패 ($TARGET_MONTH)

검증은 통과했지만 실제 적용(manage.py compact_payment_fees) 단계에서
오류가 발생했습니다. 로그를 확인해주세요: /home/horeb/logs/compact_payment_fees.log"
    python manage.py shell -c "
import os
from django.conf import settings
from utils.telegram import send_telegram_sync
from utils.email import send_text_email
msg = os.environ['ALERT_MSG']
send_telegram_sync(msg)
send_text_email('compact_payment_fees 실행 실패 ($TARGET_MONTH)', msg, [settings.RECIPIENT_EMAIL])
" || true
    exit 1
fi
