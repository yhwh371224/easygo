from django.core.cache import cache


def build_user_prompt(sender, subject, body, history_text):
    return f"""[Email History]
{history_text}

[New Email]
From: {sender}
Subject: {subject}
Body:
{body}
"""

