class GmailDraftService:

    def build_comparison_draft(self, to, subject, thread_id, analysis_result):
        """
        Create a Gmail draft containing both Claude and OpenAI replies side by side.
        `subject` should be the raw subject (no "Re:" prefix — create_gmail_draft adds it).
        Returns the created draft ID.
        """
        from email_agent.tasks import get_gmail_service, create_gmail_draft

        openai_reply = analysis_result["openai"]["suggested_reply"]
        claude_reply = analysis_result["claude"]["suggested_reply"]

        body = f"""================================================
OPENAI VERSION
================================================
{openai_reply}


================================================
CLAUDE VERSION
================================================
{claude_reply}"""

        service = get_gmail_service()
        return create_gmail_draft(service, to, subject, body, thread_id=thread_id)
