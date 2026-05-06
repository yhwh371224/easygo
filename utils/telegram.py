import requests
from django.conf import settings

import os


def is_test_env():
    return os.environ.get("PYTEST_RUNNING") == "1"


async def send_telegram_notification(text: str):
    if is_test_env():
        return
    
    import telegram
    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id=settings.TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="Markdown",
    )


def send_telegram_sync(text: str):
    if is_test_env():
        return

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    

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