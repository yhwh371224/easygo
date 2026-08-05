import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from posting_agent.telegram_bot import load_pending_review, clear_pending_review
from posting_agent.review_manager import post_reply


logging.basicConfig(level=logging.INFO)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("ra:"):
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
    help = 'Run Telegram bot for review-reply approval'

    def handle(self, *args, **options):
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CallbackQueryHandler(button_handler))
        self.stdout.write(self.style.SUCCESS("🤖 Telegram bot running..."))
        app.run_polling()
