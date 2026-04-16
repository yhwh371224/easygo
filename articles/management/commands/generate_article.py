import asyncio
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from telegram.ext import Application, CallbackQueryHandler

from articles.models import Category, Post
from posting_agent.telegram_bot import send_article_notification
from posting_agent.management.commands.run_telegram_bot import button_handler
from services.claude_service import ClaudeService

_claude = ClaudeService()


def generate_article_content(topic: str, category_name: str) -> dict:
    system_prompt = """You are a content writer for EasyGo Airport Shuttle, a professional airport transfer service in Sydney, Australia.

Write in direct, practical Australian English (travelling, colour, harbour, etc.).
Address the reader as "you". Mention EasyGo factually — no hype.
Never fabricate prices, statistics, or facts you are not certain about."""

    user_prompt = f"""Write a complete blog post about: "{topic}"
Category: "{category_name}"

Return ONLY this exact format with no extra text outside the markers:

===TITLE===
[SEO-optimized blog title. Max 60 characters.]

===SLUG===
[URL-friendly slug using hyphens. Lowercase only. e.g. sydney-airport-group-travel-tips]

===EXCERPT===
[2-3 sentence summary for list pages. Max 280 characters.]

===CONTENT===
Write a full blog post in clean HTML following EVERY rule below.

────────────────────────────────
STRUCTURE (must follow this order)
────────────────────────────────
1. INTRO — one <p> paragraph: state the problem or question the reader has and why it matters.
2. BODY — 3 to 5 <h2> sections. Each section covers one option, factor, or sub-topic with 1–3 <p> paragraphs and/or <ul>/<li> lists.
3. COMPARISON TABLE — 1 or 2 tables (see exact HTML below) that visualise the key differences or data points.
4. TIP BOXES — 2 to 3 tip boxes (see exact HTML below) scattered between sections, not all grouped at the end.
5. EASYGO SECTION — one dedicated <h2> that introduces EasyGo Airport Shuttle naturally and explains how it relates to the topic.
6. CTA CLOSING — final <p> or short section with a call to action. Use the internal links listed below where relevant.

────────────────────────────────
HTML COMPONENTS (copy exactly)
────────────────────────────────

TIP BOX:
<div class="tip-box">
  [tip content here]
</div>

COMPARISON TABLE:
<table style="width:100%; border-collapse:collapse; font-family:'DM Sans',sans-serif; font-size:.92rem; margin-bottom:24px;">
  <thead>
    <tr style="background:#0d6efd; color:#fff;">
      <th style="padding:10px 14px; text-align:left;">[Column heading]</th>
      <th style="padding:10px 14px; text-align:left;">[Column heading]</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-bottom:1px solid #e2e8f0;">
      <td style="padding:10px 14px;">[value]</td>
      <td style="padding:10px 14px;">[value]</td>
    </tr>
    <tr style="background:#f5f7fa; border-bottom:1px solid #e2e8f0;">
      <td style="padding:10px 14px;">[value]</td>
      <td style="padding:10px 14px;">[value]</td>
    </tr>
  </tbody>
</table>

────────────────────────────────
INTERNAL LINKS (use naturally where topic is relevant — do not force all of them)
────────────────────────────────
- <a href="/">EasyGo Airport Shuttle</a>
- <a href="/maxi-taxi/">maxi taxi</a> or <a href="/maxi-taxi/">maxi van</a>
- <a href="/inquiry/">Get an instant price quote</a>
- <a href="/booking/">book your transfer</a>
- <a href="/contact/">Send us a message</a>
- <a href="/meeting_point/">terminal meeting point</a>
- <a href="https://easygoshuttle.com.au/sovereign_chauffeurs_v2/">luxury chauffeur</a>

────────────────────────────────
REQUIREMENTS CHECKLIST
────────────────────────────────
- Minimum 900 words
- At least 2 tip boxes (class="tip-box")
- At least 1 comparison table (exact inline styles above)
- EasyGo mentioned naturally 2–3 times total
- No <html>, <head>, or <body> tags
- No inline CSS except inside the table and tip-box components above
- Australian English spelling throughout

===META_TITLE===
[SEO meta title. Max 60 characters. Include primary keyword.]

===META_DESCRIPTION===
[SEO meta description. Max 155 characters. Include a call to action.]

===GMB_CONTENT===
[Google Business Profile post. 150-200 words. Professional and engaging. Mention EasyGo Airport Shuttle naturally. Include key benefits: fixed pricing, door-to-door, flight tracking. End with call to action. No hashtags. Must be under 1000 characters.]

===THUMBNAIL_QUERY===
[2-4 keywords for Unsplash image search. Simple and specific. e.g. "sydney airport terminal shuttle"]"""

    raw = _claude.generate(system_prompt, user_prompt, max_tokens=6000)
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
        parser.add_argument('--topic',    default=None, help='Topic or title for the article')
        parser.add_argument('--category', default=None, help='Category name (must already exist in DB)')

    def handle(self, *args, **options):
        # --- topic ---
        topic = options['topic']
        while not topic or not topic.strip():
            topic = input("\n🖊  Topic (블로그 주제): ").strip()

        # --- category ---
        existing = list(Category.objects.values_list('name', flat=True))
        category_name = options['category']
        while True:
            if not category_name or not category_name.strip():
                self.stdout.write(f"\n📂  Available categories: {', '.join(existing)}")
                category_name = input("📂  Category: ").strip()
                if not category_name:
                    continue
            try:
                category = Category.objects.get(name=category_name)
                break
            except Category.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"    '{category_name}' not found. Please try again."))
                self.stdout.write(f"📂  Available categories: {', '.join(existing)}")
                category_name = ""

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
