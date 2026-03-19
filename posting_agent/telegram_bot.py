import json
import telegram
from django.conf import settings

PENDING_FILE = '/tmp/easygo_pending_post.json'
PENDING_IMAGE_FILE = '/tmp/easygo_pending_image.webp'


def save_pending(content: dict, image_bytes: bytes):
    with open(PENDING_FILE, 'w') as f:
        json.dump(content, f)
    with open(PENDING_IMAGE_FILE, 'wb') as f:
        f.write(image_bytes)


def load_pending():
    try:
        with open(PENDING_FILE, 'r') as f:
            content = json.load(f)
        with open(PENDING_IMAGE_FILE, 'rb') as f:
            image_bytes = f.read()
        return content, image_bytes
    except FileNotFoundError:
        return None, None


def clear_pending():
    import os
    for f in [PENDING_FILE, PENDING_IMAGE_FILE]:
        if os.path.exists(f):
            os.remove(f)


async def send_preview(content: dict, image_bytes: bytes):
    save_pending(content, image_bytes)

    preview = (
        f"📋 *Post Preview*\n\n"
        f"*제목:* {content['title']}\n\n"
        f"*블로그 (SEO):*\n{content['seo_content'][:300]}...\n\n"
        f"*소셜 (FB/IG):*\n{content['social_content']}\n\n"
        f"*GMB:*\n{content['gmb_content']}"
    )

    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
    await bot.send_photo(
        chat_id=settings.TELEGRAM_CHAT_ID,
        photo=image_bytes,
        caption=preview,
        parse_mode="Markdown",
        reply_markup=telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("✅ 전체 발행", callback_data="approve_all"),
                telegram.InlineKeyboardButton("🔄 재생성", callback_data="regenerate"),
                telegram.InlineKeyboardButton("❌ 취소", callback_data="cancel"),
            ]
        ])
    )