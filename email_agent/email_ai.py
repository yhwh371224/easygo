import logging
from services.ai_router import AIRouter
from services.claude_service import ClaudeService

logger = logging.getLogger(__name__)

_router = AIRouter()
_claude = ClaudeService()


def analyze_email_with_claude(sender, subject, body, thread_history):
    return _claude.analyze_email(sender, subject, body, thread_history)


def analyze_email_dual(sender, subject, body, thread_history):
    return _router.analyze_email_dual(sender, subject, body, thread_history)
