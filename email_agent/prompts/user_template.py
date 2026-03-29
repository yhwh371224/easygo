from django.core.cache import cache


def build_user_prompt(sender, subject, body, history_text):
    return f"""[Email History - for context only, do not reply to this]
{history_text}

[New Email - reply to THIS only]
From: {sender}
Subject: {subject}
Body:
{body}

Write a reply to the [New Email] above.
"""

