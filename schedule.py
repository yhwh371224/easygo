import os.path
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from main.settings import RECIPIENT_EMAIL
from django.conf import settings 


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
LABEL_NAME = "Inquiry to confirm"
SERVICE_ACCOUNT_FILE = settings.GMAIL_SERVICE_ACCOUNT_FILE
DELEGATED_USER_EMAIL = RECIPIENT_EMAIL  # 위임받은 사용자의 이메일 주소

def get_scheduled_emails(service):
    try:
        label_id = get_label_id(service, LABEL_NAME)
        
        if label_id:
            results = service.users().messages().list(userId="me", labelIds=[label_id]).execute()
            messages = results.get("messages", [])

            if not messages:
                print("No messages found in the 'Inquiry to confirm' folder.")
                return []

            scheduled_emails = []

            for message in messages:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                headers = msg["payload"]["headers"]
                for header in headers:
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

def get_label_id(service, label_name):
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    print(f"Label '{label_name}' not found.")
    return None

def fetch_scheduled_emails():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL)

    try:
        service = build("gmail", "v1", credentials=credentials)

        scheduled_emails = get_scheduled_emails(service)

        return scheduled_emails  # Return the list

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

if __name__ == "__main__":
    scheduled_emails = fetch_scheduled_emails
    print("Scheduled Emails:", scheduled_emails)
