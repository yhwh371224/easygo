from django.core.cache import cache
from basecamp.area_full import get_more_suburbs


def build_user_prompt(sender, subject, body, history_text, suburb_list):
    if isinstance(suburb_list, list):
        suburb_str = ', '.join(suburb_list)
    else:
        suburb_str = suburb_list
    return f"""[Available Suburbs]
    
{suburb_str}

{history_text}

[New Email]
From: {sender}
Subject: {subject}
Body:
{body}"""


def get_suburb_list():
    cached = cache.get("suburb_list")
    if cached:
        return cached
    suburbs = list(get_more_suburbs().keys())
    cache.set("suburb_list", suburbs, timeout=3600)  # 1시간
    return suburbs