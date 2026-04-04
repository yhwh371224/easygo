import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from posting_agent.telegram_bot import load_pending, clear_pending, load_pending_review, clear_pending_review
from posting_agent.blog_poster import save_blog_post
from posting_agent.social_poster import post_to_facebook, post_to_instagram
from posting_agent.review_manager import post_reply
from posting_agent.gmb_poster import post_to_google_business


logging.basicConfig(level=logging.INFO)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "approve_all":
        content, image_bytes = load_pending()
        if not content:
            await query.edit_message_caption("❌ 저장된 포스트가 없어요.")
            return

        results = []

        # 1. Django 블로그 저장
        try:
            post = save_blog_post(content, image_bytes, f"{content['topic_slug']}.webp")
            results.append(f"✅ 블로그: {post.get_absolute_url()}")
        except Exception as e:
            results.append(f"❌ 블로그 실패: {e}")

        # 2. Facebook
        fb_ok = post_to_facebook(content['social_content'], image_bytes)
        results.append("✅ Facebook 발행" if fb_ok else "❌ Facebook 실패")

        # 3. Google My Business
        blog_url = f"https://easygoairportshuttle.com.au/blog/{content['topic_slug']}/"
        gmb_ok = post_to_google_business(content['gmb_content'], call_to_action_url=blog_url)
        results.append("✅ GMB 포스트 발행" if gmb_ok else "❌ GMB 실패")

        # 4. Instagram (이미지 URL 필요 - 블로그 저장 후 URL 사용)
        # TODO: Meta API 셋업 후 활성화
        results.append("⏸️ Instagram (Meta API 셋업 후 활성화)")

        clear_pending()
        await query.edit_message_caption("\n".join(results))

    elif query.data == "regenerate":
        clear_pending()
        await query.edit_message_caption("🔄 재생성: python manage.py generate_post 를 다시 실행해주세요.")

    elif query.data == "cancel":
        clear_pending()
        await query.edit_message_caption("❌ 취소됐습니다.")

    elif query.data.startswith("ra:"):
        review_id = query.data.split(":")[1]
        review, reply = load_pending_review(review_id)
        if not review:
            await query.edit_message_text("❌ 저장된 리뷰가 없어요.")
            return
        ok = post_reply(review['name'], reply)
        if ok:
            await query.edit_message_text(f"✅ 답변 발행 완료!\n\n{reply}")
        else:
            await query.edit_message_text("❌ 답변 발행 실패")
        clear_pending_review(review_id)

    elif query.data.startswith("rs:"):
        review_id = query.data.split(":")[1]
        clear_pending_review(review_id)
        await query.edit_message_text("⏭️ 건너뛰었습니다.")

    elif query.data.startswith("re:"):
        review_id = query.data.split(":")[1]
        await query.edit_message_text("✏️ 수정할 답변 내용을 입력해주세요:")


class Command(BaseCommand):
    help = 'Run Telegram bot for post approval'

    def handle(self, *args, **options):
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CallbackQueryHandler(button_handler))
        self.stdout.write(self.style.SUCCESS("🤖 Telegram bot running..."))
        app.run_polling()