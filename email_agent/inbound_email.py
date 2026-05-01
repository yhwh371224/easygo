"""
Gmail inbound pipeline: history → metadata → system filters → classification → (optional) AI reply.
"""
from __future__ import annotations

import base64
import logging
import re
from typing import Any, Literal

from django.conf import settings

logger = logging.getLogger(__name__)

Classification = Literal["airport", "other"]

# Fast keyword gate (substring match on normalized subject + body)
AIRPORT_KEYWORDS: tuple[str, ...] = (
    "airport",
    "transfer",
    "pickup",
    "drop",
    "booking",
    "reservation",
    "flight",
    "terminal",
    "shuttle",
    "taxi",
    "arrival",
    "departure",
    "luggage",
)

CONTACT_FORM_SUBJECT_MARKER = "[New Contact] Submission from"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def keywords_match_airport_intent(subject: str, body: str) -> bool:
    haystack = _normalize(f"{subject} {body}")
    return any(kw in haystack for kw in AIRPORT_KEYWORDS)


def is_contact_form_submission(subject: str) -> bool:
    return CONTACT_FORM_SUBJECT_MARKER in (subject or "")


def classify_by_keywords(subject: str, body: str) -> Classification:
    return "airport" if keywords_match_airport_intent(subject, body) else "other"


def classify_inbound_email(subject: str, body: str) -> tuple[Classification, str]:
    """
    Keyword + business rules only (no LLM).
    Returns (classification, short reason for logs).
    """
    if is_contact_form_submission(subject):
        return "airport", "contact_form_submission"
    if keywords_match_airport_intent(subject, body):
        return "airport", "airport_keywords_matched"
    return "other", "no_airport_keywords"


def ai_fallback_classify(subject: str, body: str) -> Classification:
    """
    Cheap single-shot LLM gate. Only called when EMAIL_AI_CLASSIFIER_FALLBACK is True
    and keyword classification returned other.
    """
    snippet = (body or "")[:6000]
    user_prompt = (
        "You classify customer emails for an airport shuttle company.\n"
        'Reply with exactly one uppercase word: AIRPORT or OTHER.\n'
        "- AIRPORT: airport transfer, booking, pickup/dropoff, flights, terminals, "
        "shuttle/taxi to/from airport, luggage, reservations, pricing for rides.\n"
        "- OTHER: spam, ads, personal chit-chat, recruiting, unrelated business.\n\n"
        f"Subject: {subject}\n\nBody:\n{snippet}"
    )
    system_prompt = "You output only one token: AIRPORT or OTHER. No punctuation or explanation."

    openai_only = getattr(settings, "EMAIL_AI_OPENAI_ONLY", False)
    if openai_only:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=8,
        )
        raw = (response.choices[0].message.content or "").strip().upper()
    else:
        from services.claude_service import ClaudeService

        raw = ClaudeService().generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=16,
        ).strip().upper()

    first = raw.split()[0] if raw else ""
    if first.startswith("AIRPORT"):
        return "airport"
    return "other"


def classify_with_optional_ai_fallback(
    subject: str, body: str,
) -> tuple[Classification, str]:
    """
    Keyword gate first; optional AI when keywords say OTHER.
    """
    label, reason = classify_inbound_email(subject, body)
    if label == "airport":
        return label, reason

    if not getattr(settings, "EMAIL_AI_CLASSIFIER_FALLBACK", False):
        return "other", reason

    ai_label = ai_fallback_classify(subject, body)
    if ai_label == "airport":
        return "airport", "ai_fallback_classifier_airport"
    return "other", "ai_fallback_classifier_other"


def extract_plain_body_from_payload(payload: dict[str, Any]) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def extract_inbox_message_ids_from_history(history_response: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for record in history_response.get("history", []):
        for msg in record.get("messagesAdded", []):
            message = msg.get("message") or {}
            if "INBOX" in message.get("labelIds", []):
                mid = message.get("id")
                if mid:
                    ids.append(mid)
    return ids


def load_message_metadata(service, msg_id: str) -> dict[str, Any]:
    return (
        service.users()
        .messages()
        .get(
            userId="me",
            id=msg_id,
            format="metadata",
            metadataHeaders=["From", "Subject"],
        )
        .execute()
    )


def load_full_message(service, msg_id: str) -> dict[str, Any]:
    return (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )


def headers_dict_from_message(email: dict[str, Any]) -> dict[str, str]:
    headers = email.get("payload", {}).get("headers") or []
    return {h["name"]: h["value"] for h in headers if "name" in h and "value" in h}


def system_filter_skip_reason(
    label_ids: list[str],
    sender: str,
    subject: str,
    processed_label_id: str,
    own_email: str,
) -> str | None:
    """
    Return a human-readable skip reason, or None if the message should continue.
    """
    if "INBOX" not in label_ids:
        return "Skipping: not INBOX"
    if "DRAFT" in label_ids:
        return "Skipping: DRAFT"
    if "SENT" in label_ids:
        return "Skipping: SENT"
    if processed_label_id in label_ids:
        return "Skipping: already processed label exists"
    if own_email in sender and not is_contact_form_submission(subject):
        return "Skipping: own outbound / internal email"
    return None


def get_thread_history(service, thread_id: str, max_messages: int = 3) -> list[dict[str, str]]:
    thread = (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="full")
        .execute()
    )
    messages = thread.get("messages", [])[-max_messages:]
    history: list[dict[str, str]] = []
    for msg in messages:
        headers = headers_dict_from_message(msg)
        body = extract_plain_body_from_payload(msg.get("payload") or {})
        history.append(
            {
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "subject": headers.get("Subject", ""),
                "body": body,
            }
        )
    return history


def reply_to_address(subject: str, body: str, sender: str) -> str:
    if is_contact_form_submission(subject):
        match = re.search(r"email:\s*(\S+)", body)
        return match.group(1) if match else sender
    return sender
