import logging

from services.claude_service import ClaudeService
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class AIRouter:

    def __init__(self):
        self.claude = ClaudeService()
        self.openai = OpenAIService()

    def analyze_email_dual(self, sender, subject, body, thread_history):
        """
        Run BOTH models for comparison (TEST MODE)
        """

        logger.info("[AI Router] DUAL MODE START")

        openai_result = self.openai.analyze_email(
            sender, subject, body, thread_history
        )

        claude_result = self.claude.analyze_email(
            sender, subject, body, thread_history
        )

        logger.info(f"[AI Router] DUAL MODE DONE | subject={subject}")

        return {
            "openai": openai_result,
            "claude": claude_result,
        }