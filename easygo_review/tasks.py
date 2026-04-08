import anthropic
from celery import shared_task
from django.conf import settings
from markdownx.utils import markdownify

EASYGO_AUTHOR = "EasyGo"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_review_reply(self, post_pk: int):
    """Generate a Claude AI reply for a review and save it as a Comment (author='EasyGo')."""
    from easygo_review.models import Comment, Post

    try:
        post = Post.objects.get(pk=post_pk)
    except Post.DoesNotExist:
        print(f"[review_reply] Post {post_pk} not found.")
        return

    if Comment.objects.filter(post=post, author=EASYGO_AUTHOR).exists():
        print(f"[review_reply] Post {post_pk} already has an EasyGo reply, skipping.")
        return

    reviewer = post.name or "valued customer"
    stars = post.rating
    # Strip markdown so the prompt gets plain text
    review_text = markdownify(post.content or "").strip() or ""

    prompt = f"""You are a professional customer service manager for EasyGo Airport Shuttle, a premium airport transfer service in Sydney, Australia.

Write a warm, professional reply to this Google review.

Reviewer: {reviewer}
Star rating: {stars}/5
Review: {review_text}

Guidelines:
- Keep it concise (2-4 sentences)
- Thank them genuinely
- If negative (1-2 stars): apologize sincerely, offer to make it right
- If positive (4-5 stars): express gratitude, invite them back
- Mention EasyGo Airport Shuttle naturally once
- Do NOT use generic phrases like "We value your feedback"
- Write in the same language as the review

Reply only, no preamble."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        print(f"[review_reply] Anthropic API error for Post {post_pk}: {exc}")
        raise self.retry(exc=exc)

    reply_text = message.content[0].text.strip()
    Comment.objects.create(post=post, author=EASYGO_AUTHOR, text=reply_text)
    print(f"[review_reply] Reply comment saved for Post {post_pk}.")
