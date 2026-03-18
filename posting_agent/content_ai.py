from django.conf import settings
import anthropic


def generate_post_content():
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": """Write a short Google Business post for EasyGo Airport Shuttle in Sydney, Australia.

Requirements:
- 2-3 sentences max
- Professional and friendly tone
- Highlight reliability, punctuality, or comfort
- End with a subtle call to action (e.g. book online)
- No emojis, no hashtags

Output only the post text."""
        }]
    )

    return message.content[0].text.strip()