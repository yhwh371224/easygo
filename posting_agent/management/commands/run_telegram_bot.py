import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from posting_agent.telegram_bot import load_pending, clear_pending
from posting_agent.gmb_poster import post_to_google_business

logging.basicConfig(level=logging.INFO)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "approve":
        text, image_bytes = load_pending()
        if not text:
            await query.edit_message_caption("❌ 저장된 포스트가 없어요. 다시 generate_post 실행해주세요.")
            return

        success = post_to_google_business(text, image_bytes)
        if success:
            clear_pending()
            await query.edit_message_caption("✅ 포스팅 완료!")
        else:
            await query.edit_message_caption("❌ 포스팅 실패. 다시 시도해주세요.")

    elif query.data == "regenerate":
        clear_pending()
        await query.edit_message_caption("🔄 재생성하려면 generate_post 를 다시 실행해주세요.")

    elif query.data == "cancel":
        clear_pending()
        await query.edit_message_caption("❌ 취소됐습니다.")


class Command(BaseCommand):
    help = 'Run Telegram bot for post approval (polling)'

    def handle(self, *args, **options):
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CallbackQueryHandler(button_handler))
        self.stdout.write(self.style.SUCCESS("Telegram bot running (polling)..."))
        app.run_polling()
