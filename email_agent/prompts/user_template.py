import logging

logger = logging.getLogger('email_agent')  # settings.py의 'email_agent' logger 사용


def build_user_prompt(sender, subject, body, history_text):
    prompt = f"""[Email History - for context only, do not reply to this]
{history_text}

[New Email - reply to THIS only]
From: {sender}
Subject: {subject}
Body:
{body}

Write a reply to the [New Email] above.
"""
    # ✅ 로깅
    logger.info("===== FINAL PROMPT =====")
    logger.info(prompt)
    logger.info("========================")

    return prompt

