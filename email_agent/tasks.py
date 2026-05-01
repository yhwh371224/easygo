import base64
import logging
import os

from celery import shared_task
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from services.gmail_draft_service import GmailDraftService

from .email_ai import analyze_email_dual, analyze_email_with_claude, analyze_email_with_openai
from .inbound_email import (
    classify_with_optional_ai_fallback,
    extract_inbox_message_ids_from_history,
    extract_plain_body_from_payload,
    get_thread_history,
    headers_dict_from_message,
    load_full_message,
    load_message_metadata,
    reply_to_address,
    system_filter_skip_reason,
)

logger = logging.getLogger(__name__)

LAST_HISTORY_ID_FILE = os.path.join(settings.BASE_DIR, "scripts", "last_history_id.txt")
PROCESSED_LABEL_ID = "Label_956123326350558597"
DUAL_MODE = getattr(settings, "EMAIL_AI_DUAL_MODE", False)
OPENAI_ONLY = getattr(settings, "EMAIL_AI_OPENAI_ONLY", False)
OWN_INBOX_ADDRESS = "info@easygoshuttle.com.au"

EMAIL_SIGNATURE = """
<p style="font-family: Arial, sans-serif; font-size: 12px; color: #555;"><strong>EasyGo Airport Shuttle</strong></p>
"""


def is_message_processed(service, msg_id):
    email = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="metadata", metadataHeaders=["labelIds"])
        .execute()
    )
    return PROCESSED_LABEL_ID in email.get("labelIds", [])


def mark_message_processed(service, msg_id):
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": [PROCESSED_LABEL_ID]},
    ).execute()


def get_last_history_id():
    if os.path.exists(LAST_HISTORY_ID_FILE):
        with open(LAST_HISTORY_ID_FILE, "r") as f:
            return f.read().strip()
    return None


def save_last_history_id(history_id):
    current = get_last_history_id()
    if not current or int(history_id) > int(current):
        with open(LAST_HISTORY_ID_FILE, "w") as f:
            f.write(str(history_id))
        return True
    return False


def get_gmail_service():
    scopes = ["https://mail.google.com/"]
    creds = service_account.Credentials.from_service_account_file(
        settings.GMAIL_SERVICE_ACCOUNT_FILE,
        scopes=scopes,
        subject=OWN_INBOX_ADDRESS,
    )
    return build("gmail", "v1", credentials=creds)


def create_gmail_draft(service, to, subject, body, thread_id=None):
    msg = MIMEMultipart("related")
    msg["to"] = to
    msg["subject"] = f"Re: {subject}" if subject else "Re: Your Inquiry"

    html_body = body.replace("\n", "<br>")

    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
{html_body}
</body>
</html>
"""

    html_part = MIMEText(html_content, "html")
    msg.attach(html_part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    draft_body = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()

    logger.info("Draft created: %s", draft.get("id"))

    draft_msg_id = draft.get("message", {}).get("id")
    if draft_msg_id:
        try:
            service.users().messages().modify(
                userId="me",
                id=draft_msg_id,
                body={"removeLabelIds": ["INBOX"]},
            ).execute()
        except Exception as e:
            logger.warning("Failed to remove INBOX label from draft: %s", e)

    return draft["id"]


def _log_skip_non_airport(msg_id: str, detail_reason: str) -> None:
    """User-facing skip lines; map internal classifier reasons to required log text."""
    if detail_reason == "no_airport_keywords" and not getattr(
        settings, "EMAIL_AI_CLASSIFIER_FALLBACK", False
    ):
        logger.info("Skipping message %s: no airport keywords", msg_id)
    else:
        logger.info("Skipping message %s: classified as OTHER (%s)", msg_id, detail_reason)


def _run_ai_reply_and_draft(
    service,
    msg_id: str,
    *,
    sender: str,
    reply_to: str,
    subject: str,
    body: str,
    thread_id: str,
    thread_history_without_current: list,
) -> None:
    """Steps 6–7: full AI analysis (existing dual / OpenAI / Claude paths) + draft."""
    if OPENAI_ONLY:
        try:
            result = analyze_email_with_openai(
                sender, subject, body, thread_history_without_current
            )
        except Exception as e:
            logger.exception("OpenAI API failed for message %s: %s", msg_id, e)
            return

        if not result:
            logger.warning("OpenAI API returned empty for message %s", msg_id)
            return

        reply_body = result["suggested_reply"] + EMAIL_SIGNATURE
        try:
            create_gmail_draft(service, reply_to, subject, reply_body, thread_id=thread_id)
            mark_message_processed(service, msg_id)
        except Exception as e:
            logger.exception("Draft creation failed for message %s: %s", msg_id, e)

    elif DUAL_MODE:
        try:
            dual_result = analyze_email_dual(
                sender, subject, body, thread_history_without_current
            )
            GmailDraftService().build_comparison_draft(
                to=reply_to,
                subject=subject,
                thread_id=thread_id,
                analysis_result=dual_result,
            )
            mark_message_processed(service, msg_id)
        except Exception as e:
            logger.exception("Dual mode draft creation failed for message %s: %s", msg_id, e)
    else:
        try:
            result = analyze_email_with_claude(
                sender, subject, body, thread_history_without_current
            )
        except Exception as e:
            logger.exception("Claude API failed for message %s: %s", msg_id, e)
            return

        if not result:
            logger.warning("Claude API returned empty for message %s", msg_id)
            return

        reply_body = result["suggested_reply"] + EMAIL_SIGNATURE
        try:
            create_gmail_draft(service, reply_to, subject, reply_body, thread_id=thread_id)
            mark_message_processed(service, msg_id)
        except Exception as e:
            logger.exception("Draft creation failed for message %s: %s", msg_id, e)


@shared_task
def gmail_watch_topic(payload):
    """
    Pub/Sub → Gmail history → message IDs → metadata → system filters →
    airport classification → (airport only) AI reply → draft → processed label.
    """
    service = get_gmail_service()

    history_id = payload.get("historyId")
    if not history_id:
        return
    history_id = str(history_id)

    start_history_id = get_last_history_id()
    if not start_history_id:
        start_history_id = str(int(history_id) - 10)

    if int(history_id) <= int(start_history_id):
        logger.info("Already processed historyId %s, skipping", history_id)
        return

    if not save_last_history_id(history_id):
        logger.info("historyId %s already being processed, skipping", history_id)
        return

    try:
        # 1) Fetch Gmail history (INBOX additions only)
        history_response = (
            service.users()
            .history()
            .list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
            )
            .execute()
        )

        # 2) Extract message IDs (history list pre-filters INBOX)
        message_ids = extract_inbox_message_ids_from_history(history_response)

        for msg_id in message_ids:
            # 3) Load message metadata (labels + From/Subject)
            meta = load_message_metadata(service, msg_id)
            label_ids = meta.get("labelIds", [])
            headers = headers_dict_from_message(meta)
            sender = headers.get("From", "")
            subject = headers.get("Subject", "")

            # 4) System filters (no full body yet)
            skip_reason = system_filter_skip_reason(
                label_ids,
                sender,
                subject,
                PROCESSED_LABEL_ID,
                OWN_INBOX_ADDRESS,
            )
            if skip_reason:
                logger.info("Skipping message %s: %s", msg_id, skip_reason)
                if "own outbound" in skip_reason.lower():
                    mark_message_processed(service, msg_id)
                continue

            # 5) Full message for body + classification
            full_email = load_full_message(service, msg_id)
            body = extract_plain_body_from_payload(full_email.get("payload") or {})
            thread_id = full_email["threadId"]

            classification, cls_detail = classify_with_optional_ai_fallback(subject, body)
            if classification != "airport":
                _log_skip_non_airport(msg_id, cls_detail)
                mark_message_processed(service, msg_id)
                continue

            # Thread context only when we will call reply AI
            thread_history = get_thread_history(service, thread_id)
            thread_history_without_current = [
                m for m in thread_history if m.get("body", "").strip() != body.strip()
            ]

            reply_to = reply_to_address(subject, body, sender)
            logger.info(
                "Processing airport message %s | classification=%s | reply_to=%s",
                msg_id,
                cls_detail,
                reply_to,
            )

            _run_ai_reply_and_draft(
                service,
                msg_id,
                sender=sender,
                reply_to=reply_to,
                subject=subject,
                body=body,
                thread_id=thread_id,
                thread_history_without_current=thread_history_without_current,
            )

    except Exception:
        logger.exception("gmail_watch_topic failed")
