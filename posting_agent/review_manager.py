import os
from django.conf import settings
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import anthropic


def get_gmb_service():
    creds = Credentials.from_authorized_user_file(settings.GMB_TOKEN_FILE)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(settings.GMB_TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build(
        'mybusiness', 'v4',
        credentials=creds,
        discoveryServiceUrl='https://mybusiness.googleapis.com/$discovery/rest?version=v4'
    )


def get_unanswered_reviews(max_reviews=10):
    service = get_gmb_service()
    location_name = settings.GMB_LOCATION_NAME

    response = service.accounts().locations().reviews().list(
        parent=location_name,
        pageSize=50,
    ).execute()

    reviews = response.get('reviews', [])

    unanswered = [
        r for r in reviews
        if not r.get('reviewReply')
    ]

    return unanswered[:max_reviews]


def generate_reply(review: dict) -> str:
    reviewer = review.get('reviewer', {}).get('displayName', 'valued customer')
    rating = review.get('starRating', 'FIVE')
    comment = review.get('comment', '')

    rating_map = {
        'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5
    }
    stars = rating_map.get(rating, 5)

    prompt = f"""You are a professional customer service manager for EasyGo Airport Shuttle, a premium airport transfer service in Sydney, Australia.

Write a warm, professional reply to this Google review.

Reviewer: {reviewer}
Star rating: {stars}/5
Review: {comment}

Guidelines:
- Keep it concise (2-4 sentences)
- Thank them genuinely
- If negative (1-2 stars): apologize sincerely, offer to make it right
- If positive (4-5 stars): express gratitude, invite them back
- Mention EasyGo Airport Shuttle naturally once
- Do NOT use generic phrases like "We value your feedback"
- Write in the same language as the review

Reply only, no preamble."""

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def post_reply(review_name: str, reply_text: str) -> bool:
    service = get_gmb_service()
    try:
        service.accounts().locations().reviews().updateReply(
            name=review_name,
            body={'comment': reply_text}
        ).execute()
        return True
    except Exception as e:
        print(f"[GMB] Reply failed: {e}")
        return False