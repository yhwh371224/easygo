import logging
import anthropic
from django.conf import settings

from email_agent.prompts.company_data import FULL_COMPANY_CONTEXT
from email_agent.prompts.system_prompt import STATIC_SYSTEM_PROMPT
from email_agent.prompts.user_template import build_user_prompt

logger = logging.getLogger(__name__)


class ClaudeService:

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )

    def analyze_email(self, sender, subject, body, thread_history):
        """
        Main entry:
        Email → Claude analysis → structured reply
        """

        history_text = self._build_history_text(thread_history)
        user_prompt = build_user_prompt(
            sender,
            subject,
            body,
            history_text
        )

        message = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=[
                {
                    "type": "text",
                    "text": STATIC_SYSTEM_PROMPT,
                },
                {
                    "type": "text",
                    "text": FULL_COMPANY_CONTEXT,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        # ------------------------
        # Token usage logging
        # ------------------------
        usage = message.usage
        logger.info(
            f"[Claude Token Usage] subject='{subject}' | "
            f"cache_creation={usage.cache_creation_input_tokens} | "
            f"cache_read={usage.cache_read_input_tokens} | "
            f"input={usage.input_tokens} | "
            f"output={usage.output_tokens}"
        )

        text = self._extract_text(message)
        return self._parse_response(text)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
        """
        General-purpose Claude call for non-email tasks (articles, GMB posts, review replies, etc.)
        Returns raw text string, not a structured dict.
        """
        message = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        usage = message.usage
        logger.info(
            f"[Claude Token Usage] "
            f"input={usage.input_tokens} | "
            f"output={usage.output_tokens}"
        )

        return self._extract_text(message)

    # ==================================================
    # Helpers
    # ==================================================

    def _extract_text(self, message):
        """
        Safely extract Claude response text
        """
        if not message.content:
            return ""

        for block in message.content:
            if hasattr(block, "text"):
                return block.text

        return ""

    def _build_history_text(self, thread_history):
        """
        Convert email thread history into prompt-friendly text
        """
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
        """
        Clean Claude output and return structured response
        """
        response_text = response_text.strip()

        # Handle markdown code blocks if any
        if "```" in response_text:
            parts = response_text.split("```")
            if len(parts) >= 3:
                response_text = parts[1].strip()

        return {
            "suggested_reply": response_text
        }