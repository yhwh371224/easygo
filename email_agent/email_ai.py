from services.ai_router import AIRouter

_router = AIRouter()


def analyze_email_with_claude(sender, subject, body, thread_history):
    return _router.claude.analyze_email(sender, subject, body, thread_history)


def analyze_email_dual(sender, subject, body, thread_history):
    return _router.analyze_email_dual(sender, subject, body, thread_history)
