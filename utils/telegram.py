import logging
import requests
from django.conf import settings

import os

logger = logging.getLogger(__name__)


def is_test_env():
    return os.environ.get("PYTEST_RUNNING") == "1"


async def send_telegram_notification(text: str):
    if is_test_env():
        return

    import telegram
    try:
        bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=settings.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
        )
    except Exception:
        logger.warning("Failed to send Telegram notification", exc_info=True)


def send_telegram_sync(text: str):
    if is_test_env():
        return

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        # requests 는 400 에 예외를 내지 않는다. 응답을 보지 않으면 텔레그램이 거절한
        # 알림이 흔적 없이 사라진다 — 알림을 못 받은 것과 문제가 없는 것이 구분되지 않는다.
        resp = requests.post(url, data=payload, timeout=10)
        if resp.ok:
            return
        # 예약자 이름이나 이메일에 _ * [ 가 섞이면 Markdown 파싱이 400 으로 떨어진다.
        # 알림이 통째로 사라지는 것보다는 서식을 버리고 보내는 쪽이 낫다.
        logger.warning("Telegram rejected the message (%s): %s", resp.status_code, resp.text[:300])
        payload.pop("parse_mode")
        resp = requests.post(url, data=payload, timeout=10)
        if not resp.ok:
            logger.error("Telegram send failed (%s): %s", resp.status_code, resp.text[:300])
    except Exception:
        logger.warning("Failed to send Telegram notification", exc_info=True)


def get_ip_info(ip: str) -> str:
    try:
        resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        data = resp.json()
        city = data.get('city', '')
        region = data.get('region', '')
        org = data.get('org', '')
        return f"{city}, {region} ({org})"
    except Exception:
        return "Unknown"