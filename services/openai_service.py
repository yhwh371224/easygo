import logging
from django.conf import settings
from openai import OpenAI

from email_agent.prompts.company_data import FULL_COMPANY_CONTEXT
from email_agent.prompts.system_prompt import STATIC_SYSTEM_PROMPT
from email_agent.prompts.user_template import build_user_prompt

logger = logging.getLogger(__name__)


class OpenAIService:

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def analyze_email(self, sender, subject, body, thread_history):
        """
        Email → OpenAI analysis → structured reply
        """

        history_text = self._build_history_text(thread_history)
        user_prompt = build_user_prompt(sender, subject, body, history_text)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": STATIC_SYSTEM_PROMPT + "\n\n" + FULL_COMPANY_CONTEXT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.3,
        )

        text = response.choices[0].message.content

        logger.info(
            f"[OpenAI Usage] subject='{subject}' | "
            f"input={response.usage.prompt_tokens if response.usage else 'N/A'} | "
            f"output={response.usage.completion_tokens if response.usage else 'N/A'} | "
            f"total={response.usage.total_tokens if response.usage else 'N/A'}"
        )

        return self._parse_response(text)

    # ------------------------
    # Helpers
    # ------------------------

    def _build_history_text(self, thread_history):
        if not thread_history:
            return "No previous emails."

        lines = []
        for msg in thread_history:
            lines.append(
                f"From: {msg['from']}\n"
                f"Date: {msg['date']}\n"
                f"{msg['body'][:300]}\n---"
            )
        return "\n".join(lines)

    def _parse_response(self, response_text):
        response_text = response_text.strip()

        if "```" in response_text:
            parts = response_text.split("```")
            if len(parts) >= 3:
                response_text = parts[1].strip()

        return {
            "suggested_reply": response_text
        }