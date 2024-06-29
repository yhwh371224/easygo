import os.path
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from main.settings import RECIPIENT_EMAIL

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
LABEL_NAME = "Re-reminder"
EXCLUDED_EMAIL = "info+canned.response@easygoshuttle.com.au"
SERVICE_ACCOUNT_FILE = 'secure/reminder/service-account-file.json'
DELEGATED_USER_EMAIL = RECIPIENT_EMAIL  


def get_rereminder_emails(service):
    try:
        label_id = get_label_id(service, LABEL_NAME)
        
        if label_id:
            results = service.users().messages().list(userId="me", labelIds=[label_id]).execute()
            messages = results.get("messages", [])

            if not messages:
                print("No messages found with the 'Re-reminder' label.")
                return []

            rereminder_emails = []

            for message in messages:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                headers = msg["payload"]["headers"]
                for header in headers:
                    if header["name"] == "From":
                        match = re.search(r'<([^>]+)>', header["value"])
                        if match:
                            email = match.group(1).strip()
                            if email != RECIPIENT_EMAIL and email != EXCLUDED_EMAIL:                           
                                rereminder_emails.append(email)

            return rereminder_emails

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


def main():    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL)

    try:
        service = build("gmail", "v1", credentials=credentials)
        rereminder_emails = get_rereminder_emails(service)
        return rereminder_emails  

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

if __name__ == "__main__":
    rereminder_emails = main()

