import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from main.settings import RECIPIENT_EMAIL


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SERVICE_ACCOUNT_FILE = settings.GMAIL_SERVICE_ACCOUNT_FILE
DELEGATED_USER_EMAIL = RECIPIENT_EMAIL

EXCLUDED_EMAILS = [
    "info@easygoshuttle.com.au",
    "info+canned.response@easygoshuttle.com.au",
]

EMAIL_REGEX = re.compile(r'[\w\.\+\-]+@[\w\.-]+')


def _build_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL
    )
    return build("gmail", "v1", credentials=credentials)


def _get_label_id(service, label_name):
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label.get("name") == label_name:
            return label.get("id")
    print(f"Label '{label_name}' not found.")
    return None


def _extract_emails(header_value):
    if not header_value:
        return []
    return EMAIL_REGEX.findall(header_value)


def _fetch_emails_by_label(service, label_name):
    """Return all From/To emails from messages with the given label, excluding system emails."""
    label_id = _get_label_id(service, label_name)
    if not label_id:
        return []

    messages = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me", labelIds=[label_id], pageToken=page_token
        ).execute()
        messages.extend(resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    if not messages:
        print(f"No messages found with the '{label_name}' label.")
        return []

    collected = set()
    excluded_lower = {e.lower() for e in EXCLUDED_EMAILS}

    for message in messages:
        try:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
        except HttpError as e:
            print(f"Failed to fetch message {message.get('id')}: {e}")
            continue

        for header in msg.get("payload", {}).get("headers", []):
            if header.get("name", "").lower() in ("from", "to"):
                for email in _extract_emails(header.get("value", "")):
                    elow = email.lower()
                    if elow and elow not in excluded_lower:
                        collected.add(elow)

    return sorted(collected)


def fetch_reminder_emails():
    """Fetch emails from the 'Re-reminder' Gmail label."""
    try:
        service = _build_service()
        return _fetch_emails_by_label(service, "Re-reminder")
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def fetch_cash_emails():
    """Fetch emails from the 'cash' Gmail label."""
    try:
        service = _build_service()
        return _fetch_emails_by_label(service, "cash")
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def fetch_scheduled_emails():
    """Fetch sender emails from the 'Inquiry to confirm' Gmail label."""
    try:
        service = _build_service()
        label_id = _get_label_id(service, "Inquiry to confirm")
        if not label_id:
            return []

        results = service.users().messages().list(userId="me", labelIds=[label_id]).execute()
        messages = results.get("messages", [])
        if not messages:
            print("No messages found in the 'Inquiry to confirm' folder.")
            return []

        scheduled_emails = []
        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            for header in msg["payload"]["headers"]:
                if header["name"] == "From":
                    match = re.search(r'<([^>]+)>', header["value"])
                    if match:
                        email = match.group(1).strip()
                        if email != RECIPIENT_EMAIL:
                            scheduled_emails.append(email)

        return scheduled_emails

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []
