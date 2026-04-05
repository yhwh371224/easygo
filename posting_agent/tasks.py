import re

import anthropic
from celery import shared_task
from django.conf import settings


GMB_MAX_LENGTH = 1000
CLAUDE_MODEL = "claude-haiku-4-5-20251001"


def _strip_html(html: str) -> str:
    """Remove HTML tags from content."""
    return re.sub(r'<[^>]+>', '', html).strip()


def _generate_gmb_content(post) -> str:
    """Generate GMB content from post. Uses gmb_content field if set, otherwise AI summary."""
    if post.gmb_content and post.gmb_content.strip():
        return post.gmb_content[:GMB_MAX_LENGTH]

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Summarize the following blog post for a Google My Business update. "
                    f"Keep it under {GMB_MAX_LENGTH} characters. "
                    f"Make it engaging and customer-friendly. "
                    f"Naturally include relevant SEO keywords from the post. "
                    f"Focus on local search terms related to Sydney airport transfers. "
                    f"End with a subtle call to action encouraging readers to visit the website for more information.\n\n"
                    f"Title: {post.title}\n"
                    f"Meta description: {post.meta_description}\n\n"
                    f"Content:\n{_strip_html(post.content)}"
                ),
            }
        ],
    )
    summary = message.content[0].text[:GMB_MAX_LENGTH]
    post.gmb_content = summary
    post.save(update_fields=["gmb_content"])
    return summary


@shared_task
def post_to_gmb_from_article(post_pk: int):
    """Celery task: generate GMB content and post it for a given Post pk."""
    from articles.models import Post
    from posting_agent.gmb_poster import post_to_google_business
    from posting_agent.image_ai import generate_post_image

    try:
        post = Post.objects.get(pk=post_pk)
    except Post.DoesNotExist:
        print(f"Post {post_pk} not found.")
        return

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

    # Post to Google My Business
    success = post_to_google_business(
        text=gmb_text,
        image_url=image_url,
        call_to_action_url=f"{settings.SITE_URL}/blog/{post.slug}/",
    )

    # Mark as posted only if successful
    if success:
        post.posted_to_google = True
        post.save(update_fields=["posted_to_google"])
        print(f"GMB posting complete for post: {post.title}")
    else:
        print(f"GMB posting failed for post: {post.title}")