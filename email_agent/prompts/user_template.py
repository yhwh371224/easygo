from django.core.cache import cache
from .company_data import get_relevant_context


def build_user_prompt(sender, subject, body, history_text):
    context = get_relevant_context(body)  

    return f"""[Company Policy - use this to answer accurately]
{context}

[Email History - for context only, do not reply to this]
{history_text}

[New Email - reply to THIS only]
From: {sender}
Subject: {subject}
Body:
{body}

Write a reply to the [New Email] above.
"""

