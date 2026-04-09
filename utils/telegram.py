import telegram
from django.conf import settings


async def send_telegram_notification(text: str):
    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id=settings.TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="Markdown",
    )

    