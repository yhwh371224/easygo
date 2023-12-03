import os.path
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from main.settings import RECIPIENT_EMAIL

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

LABEL_NAME = "Inquiry to confirm"

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
    creds = None
    secure_directory = 'secure_gmail_1/'
    token_file_path = os.path.join(secure_directory, 'token.json')

    if os.path.exists(token_file_path):
        creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_file_path = os.path.join(secure_directory, 'credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)

        scheduled_emails = get_scheduled_emails(service)

        return scheduled_emails  # Return the list

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

if __name__ == "__main__":
    scheduled_emails = fetch_scheduled_emails
    print("Scheduled Emails:", scheduled_emails)
