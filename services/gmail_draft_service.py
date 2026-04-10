class GmailDraftService:

    def build_comparison_draft(self, analysis_result):
        subject = analysis_result["subject"]

        openai_reply = analysis_result["openai"]["suggested_reply"]
        claude_reply = analysis_result["claude"]["suggested_reply"]

        body = f"""
Subject: Re: {subject}

================================================
OPENAI VERSION
================================================
{openai_reply}

================================================
CLAUDE VERSION
================================================
{claude_reply}
"""

        return {
            "subject": f"Re: {subject}",
            "body": body
        }