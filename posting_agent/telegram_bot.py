import json
import asyncio
import telegram
from django.conf import settings

PENDING_TEXT_FILE = '/tmp/easygo_pending_post.json'
PENDING_IMAGE_FILE = '/tmp/easygo_pending_image.jpg'


def save_pending(text, image_bytes):
    with open(PENDING_TEXT_FILE, 'w') as f:
        json.dump({'text': text}, f)
    with open(PENDING_IMAGE_FILE, 'wb') as f:
        f.write(image_bytes)


def load_pending():
    try:
        with open(PENDING_TEXT_FILE, 'r') as f:
            text = json.load(f)['text']
        with open(PENDING_IMAGE_FILE, 'rb') as f:
            image_bytes = f.read()
        return text, image_bytes
    except FileNotFoundError:
        return None, None


def clear_pending():
    import os
    for f in [PENDING_TEXT_FILE, PENDING_IMAGE_FILE]:
        if os.path.exists(f):
            os.remove(f)


async def send_preview(text, image_bytes):
    save_pending(text, image_bytes)

    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
    await bot.send_photo(
        chat_id=settings.TELEGRAM_CHAT_ID,
        photo=image_bytes,
        caption=f"📋 *Post Preview*\n\n{text}",
        parse_mode="Markdown",
        reply_markup=telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("✅ 승인", callback_data="approve"),
                telegram.InlineKeyboardButton("🔄 재생성", callback_data="regenerate"),
                telegram.InlineKeyboardButton("❌ 취소", callback_data="cancel"),
            ]
        ])
    )