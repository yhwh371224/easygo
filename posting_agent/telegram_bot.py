import os
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
        # f"*소셜 (FB/IG):*\n{content['social_content']}\n\n"
        f"*GMB:*\n{content['gmb_content'][:300]}"
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


PENDING_REVIEW_FILE = '/tmp/easygo_pending_review_{review_id}.json'


def save_pending_review(review: dict, reply: str):
    review_id = review.get('reviewId', 'unknown')[:20]
    path = PENDING_REVIEW_FILE.format(review_id=review_id)
    with open(path, 'w') as f:
        json.dump({'review': review, 'reply': reply}, f, ensure_ascii=False)

def load_pending_review(review_id: str):
    path = f'/tmp/easygo_pending_review_{review_id}.json'
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data['review'], data['reply']
    except FileNotFoundError:
        return None, None

def clear_pending_review(review_id: str):
    path = f'/tmp/easygo_pending_review_{review_id}.json'
    if os.path.exists(path):
        os.remove(path)


async def send_review_for_approval(review: dict, reply: str, current: int, total: int):
    save_pending_review(review, reply)
    review_id = review.get('reviewId', 'unknown')

    reviewer = review.get('reviewer', {}).get('displayName', '익명')
    rating = review.get('starRating', 'FIVE')
    comment = review.get('comment', '내용 없음')

    rating_map = {'ONE': '⭐', 'TWO': '⭐⭐', 'THREE': '⭐⭐⭐', 'FOUR': '⭐⭐⭐⭐', 'FIVE': '⭐⭐⭐⭐⭐'}
    stars = rating_map.get(rating, '⭐⭐⭐⭐⭐')

    # reviewId 앞 20자만 사용
    short_id = review_id[:20]

    message = (
        f"💬 *리뷰 답변 승인 ({current}/{total})*\n\n"
        f"*리뷰어:* {reviewer}\n"
        f"*별점:* {stars}\n"
        f"*리뷰:*\n{comment}\n\n"
        f"*AI 답변 초안:*\n{reply}"
    )

    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id=settings.TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="Markdown",
        reply_markup=telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("✅ 승인", callback_data=f"ra:{short_id}"),
                telegram.InlineKeyboardButton("✏️ 수정", callback_data=f"re:{short_id}"),
                telegram.InlineKeyboardButton("⏭️ 건너뛰기", callback_data=f"rs:{short_id}"),
            ]
        ])
    )
