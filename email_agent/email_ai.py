import anthropic
import json
from django.conf import settings
from email_agent.prompts.system_prompt import STATIC_SYSTEM_PROMPT
from email_agent.prompts.user_template import build_user_prompt


def analyze_email_with_claude(sender, subject, body, thread_history):
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    history_text = _build_history_text(thread_history)
    user_prompt = build_user_prompt(sender, subject, body, history_text)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=[
            {
                "type": "text",
                "text": STATIC_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    return _parse_response(message.content[0].text)


def _build_history_text(thread_history):
    if not thread_history:
        return "No previous emails."
    lines = []
    for msg in thread_history:
        lines.append(f"From: {msg['from']}\nDate: {msg['date']}\n{msg['body'][:300]}\n---")
    return "\n".join(lines)


def _parse_response(response_text):
    response_text = response_text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        response_text = response_text.strip().rstrip("```")
        
    return {"suggested_reply": response_text}