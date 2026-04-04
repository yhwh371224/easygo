import asyncio
from django.core.management.base import BaseCommand
from posting_agent.content_ai import pick_topic, generate_all_content
from posting_agent.image_ai import generate_post_image
from posting_agent.telegram_bot import send_preview
from django.conf import settings
from telegram.ext import Application, CallbackQueryHandler
from posting_agent.management.commands.run_telegram_bot import button_handler


class Command(BaseCommand):
    help = 'Generate post content and send to Telegram for approval'

    def handle(self, *args, **options):
        self.stdout.write("🔍 토픽 선정 중...")
        topic_slug, topic_title = pick_topic()
        self.stdout.write(f"📌 선정된 토픽: {topic_title}")

        self.stdout.write("✍️  글 생성 중...")
        content = generate_all_content(topic_slug, topic_title)

        self.stdout.write("🎨 이미지 생성 중...")
        image_result = generate_post_image(
            alt_text=content['image_alt'],
            filename_slug=topic_slug,
            query=content['image_query'],
        )
        content['image_url'] = image_result.get('source_url')

        self.stdout.write("📨 Telegram 미리보기 전송 중...")
        asyncio.run(send_preview(content, image_result['image_bytes']))

        self.stdout.write("🤖 Telegram 봇 시작 - 승인 후 Ctrl+C 로 종료하세요")
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()