import asyncio
from django.core.management.base import BaseCommand
from posting_agent.content_ai import generate_post_content
from posting_agent.image_ai import generate_post_image
from posting_agent.telegram_bot import send_preview


class Command(BaseCommand):
    help = 'Generate and preview a Google Business post via Telegram'

    def handle(self, *args, **options):
        self.stdout.write("Generating post content...")
        text = generate_post_content()

        self.stdout.write("Generating image...")
        image_bytes = generate_post_image()

        self.stdout.write("Sending preview to Telegram...")
        asyncio.run(send_preview(text, image_bytes))

        self.stdout.write(self.style.SUCCESS("Preview sent! Waiting for approval in Telegram."))