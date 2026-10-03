import logging

logger = logging.getLogger('email_agent')  # settings.py의 'email_agent' logger 사용


def build_user_prompt(sender, subject, body, history_text):
    prompt = f"""[Email]
From: {sender}
Subject: {subject}
Body:
{body}

Write a reply to the email above, based only on its content.
"""
    # ✅ 로깅
    logger.info("===== FINAL PROMPT =====")
    logger.info(prompt)
    logger.info("========================")

    return prompt

