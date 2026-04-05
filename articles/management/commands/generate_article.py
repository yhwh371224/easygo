import asyncio
import anthropic
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from telegram.ext import Application, CallbackQueryHandler

from articles.models import Category, Post
from posting_agent.telegram_bot import send_article_notification
from posting_agent.management.commands.run_telegram_bot import button_handler


def generate_article_content(topic: str, category_name: str) -> dict:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"""You are a content writer for EasyGo Airport Shuttle, a professional airport transfer service in Sydney, Australia.

Write a complete blog post about: "{topic}"
Category: "{category_name}"

Return ONLY this exact format with no extra text outside the markers:

===TITLE===
[SEO-optimized blog title. Max 60 characters.]

===SLUG===
[URL-friendly slug using hyphens. Lowercase only. e.g. sydney-airport-group-travel-tips]

===EXCERPT===
[2-3 sentence summary for list pages. Max 280 characters.]

===CONTENT===
[Full blog post in clean HTML. Use <h2>, <h3>, <p>, <ul>, <li>, <strong> tags. No <html>, <head>, <body> tags. Min 600 words. Include practical advice relevant to Sydney airport transfers. Mention EasyGo naturally 2-3 times.]

===META_TITLE===
[SEO meta title. Max 60 characters. Include primary keyword.]

===META_DESCRIPTION===
[SEO meta description. Max 155 characters. Include a call to action.]

===GMB_CONTENT===
[Google Business Profile post. 150-200 words. Professional and engaging. Mention EasyGo Airport Shuttle naturally. Include key benefits: fixed pricing, door-to-door, flight tracking. End with call to action. No hashtags. Must be under 1000 characters.]

===THUMBNAIL_QUERY===
[2-4 keywords for Unsplash image search. Simple and specific. e.g. "sydney airport terminal shuttle"]"""
        }]
    )

    raw = message.content[0].text.strip()
    return parse_response(raw)


def parse_response(raw: str) -> dict:
    def extract(tag):
        start = raw.find(f"==={tag}===")
        if start == -1:
            return ""
        start += len(f"==={tag}===")
        end = raw.find("===", start)
        return raw[start:end].strip() if end != -1 else raw[start:].strip()

    return {
        "title":            extract("TITLE"),
        "slug":             extract("SLUG"),
        "excerpt":          extract("EXCERPT"),
        "content":          extract("CONTENT"),
        "meta_title":       extract("META_TITLE"),
        "meta_description": extract("META_DESCRIPTION"),
        "gmb_content":      extract("GMB_CONTENT"),
        "thumbnail_query":  extract("THUMBNAIL_QUERY"),
    }


class Command(BaseCommand):
    help = 'Generate a blog article with AI and save as draft'

    def add_arguments(self, parser):
        parser.add_argument('--topic',    required=True, help='Topic or title for the article')
        parser.add_argument('--category', required=True, help='Category name (must already exist in DB)')

    def handle(self, *args, **options):
        topic         = options['topic']
        category_name = options['category']

        # 카테고리 조회
        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            existing = list(Category.objects.values_list('name', flat=True))
            raise CommandError(
                f"Category '{category_name}' not found.\n"
                f"Available categories: {existing}"
            )

        self.stdout.write(f"Topic    : {topic}")
        self.stdout.write(f"Category : {category_name}")
        self.stdout.write("🤖 AI가 블로그 글을 생성 중입니다... 잠시만 기다려주세요.")

        data = generate_article_content(topic, category_name)

        # slug 중복 방지
        base_slug = data['slug'] or slugify(data['title'], allow_unicode=True)
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # gmb_content 1000자 초과 방지
        gmb = data['gmb_content']
        if len(gmb) > 1000:
            gmb = gmb[:997] + "..."

        post = Post.objects.create(
            title            = data['title'],
            slug             = slug,
            excerpt          = data['excerpt'],
            content          = data['content'],
            meta_title       = data['meta_title'],
            meta_description = data['meta_description'],
            gmb_content      = gmb,
            thumbnail_query  = data['thumbnail_query'],
            category         = category,
            status           = 'draft',
        )

        admin_url = f"{settings.SITE_URL}/admin/articles/post/{post.id}/change/"

        self.stdout.write(self.style.SUCCESS("\n✅ 블로그 글 초안이 생성되었습니다. 텔레그램을 확인해주세요."))
        self.stdout.write(f"  ID    : {post.id}")
        self.stdout.write(f"  Title : {post.title}")
        self.stdout.write(f"  Slug  : {post.slug}")
        self.stdout.write(f"  Admin : {admin_url}")

        asyncio.run(send_article_notification(
            post_id   = post.id,
            title     = post.title,
            category  = category.name,
            excerpt   = post.excerpt,
            admin_url = admin_url,
        ))
        self.stdout.write("📱 텔레그램으로 알림을 전송했습니다. 어드민에서 내용 확인 후 승인 버튼을 눌러주세요.")

        self.stdout.write("⏳ 봇이 대기 중입니다. 승인 후 Ctrl+C 로 종료하세요.")
        app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CallbackQueryHandler(button_handler))
        app.run_polling()
