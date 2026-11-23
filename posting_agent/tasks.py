import io
import logging
from urllib.parse import urlparse

import requests
from celery import shared_task
from django.conf import settings
from services.claude_service import ClaudeService

GMB_MAX_LENGTH = 1000

logger = logging.getLogger(__name__)

_claude = ClaudeService()


def _generate_gmb_content(post) -> str:
    """Generate GMB content from post. Uses gmb_content field if set, otherwise AI summary."""
    if post.gmb_content and post.gmb_content.strip():
        return post.gmb_content[:GMB_MAX_LENGTH]

    system_prompt = "You are a content writer for EasyGo Airport Shuttle, a professional airport transfer service in Sydney, Australia."
    user_prompt = (
        f"Write a Google My Business post under {GMB_MAX_LENGTH} characters. "
        f"Make it engaging and customer-friendly. "
        f"Naturally include relevant SEO keywords. "
        f"Focus on local search terms related to Sydney airport transfers. "
        f"End with a subtle call to action encouraging readers to visit the website for more information.\n\n"
        f"Title: {post.title}\n"
        f"Meta description: {post.meta_description}\n"
        f"Excerpt: {post.excerpt}"
    )

    summary = _claude.generate(system_prompt, user_prompt, max_tokens=1024)[:GMB_MAX_LENGTH]
    post.gmb_content = summary
    post.save(update_fields=["gmb_content"])
    return summary


def _alert_staff(text):
    """GBP 게시 실패는 로그(celery.log)에만 남아 아무도 모르고 지나간다 — 텔레그램으로 알린다."""
    from utils.telegram import send_telegram_sync
    try:
        send_telegram_sync(text)
    except Exception:
        logger.exception("[GMB] staff telegram alert failed")


def _gmb_image_url(post, image_url):
    """GBP API 는 사진으로 JPG/PNG 만 받는다 — .webp 를 넘기면 400 INVALID_ARGUMENT.
    우리 S3 사진은 대부분 webp 라서, webp 면 JPG 로 바꿔 사이트 media 에 올리고 그 주소를 쓴다.
    (Unsplash 주소는 확장자 없이 fm=jpg 로 오므로 그대로 둔다.)"""
    if not image_url or not urlparse(image_url).path.lower().endswith(".webp"):
        return image_url

    from PIL import Image
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    buf = io.BytesIO()
    Image.open(io.BytesIO(resp.content)).convert("RGB").save(buf, "JPEG", quality=88)

    path = f"articles/gmb/{post.slug}.jpg"
    if default_storage.exists(path):
        default_storage.delete(path)
    name = default_storage.save(path, ContentFile(buf.getvalue()))
    url = default_storage.url(name)
    return f"{settings.SITE_URL}{url}" if url.startswith("/") else url


@shared_task
def post_to_gmb_from_article(post_pk: int):
    """Celery task: generate GMB content and post it for a given Post pk."""
    from articles.models import Post

    try:
        post = Post.objects.get(pk=post_pk)
    except Post.DoesNotExist:
        print(f"Post {post_pk} not found.")
        return

    try:
        ok, detail = _post_article_to_gmb(post)
    except Exception as exc:
        logger.exception("[GMB] posting crashed for post %s", post_pk)
        ok, detail = False, f"{type(exc).__name__}: {exc}"

    if ok:
        post.posted_to_google = True
        post.save(update_fields=["posted_to_google"])
        print(f"GMB posting complete for post: {post.title}")
    else:
        print(f"GMB posting failed for post: {post.title}")
        _alert_staff(
            f"❌ GBP 게시 실패 | blog #{post.pk} {post.title}\n{detail}\n"
            f"고친 뒤 다시 올리기: `post_to_gmb_from_article({post.pk})`"
        )


def _post_article_to_gmb(post):
    from posting_agent.gmb_poster import post_to_google_business
    from posting_agent.image_ai import generate_post_image

    # Generate GMB text (custom field or AI summary)
    gmb_text = _generate_gmb_content(post)

    # Image URL: use stored Unsplash URL if available, otherwise fetch via generate_post_image()
    if post.thumbnail_source_url:
        image_url = post.thumbnail_source_url
    else:
        try:
            image_data = generate_post_image(
                alt_text=post.title,
                filename_slug=post.slug,
                query=post.thumbnail_query or None,
            )
            image_url = image_data.get("source_url") or None
        except ValueError:
            image_url = None  # Post text-only if all image sources fail

    try:
        image_url = _gmb_image_url(post, image_url)
    except Exception as exc:
        # 변환이 안 되면 사진 없이라도 올린다 — 대신 알린다.
        logger.warning("[GMB] webp→jpg conversion failed for post %s: %s", post.pk, exc)
        _alert_staff(f"⚠️ GBP 사진 JPG 변환 실패 — 사진 없이 게시합니다 | blog #{post.pk} {post.title}\n{exc}")
        image_url = None

    # Post to Google My Business
    return post_to_google_business(
        text=gmb_text,
        image_url=image_url,
        call_to_action_url=f"{settings.SITE_URL}/articles/blog/{post.slug}/",
    )
