from celery import shared_task
from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.conf import settings
import os


LAST_HISTORY_ID_FILE = '/home/horeb/github/easygo/last_history_id.txt'


def get_last_history_id():
    if os.path.exists(LAST_HISTORY_ID_FILE):
        with open(LAST_HISTORY_ID_FILE, 'r') as f:
            return f.read().strip()
    return None


def save_last_history_id(history_id):
    with open(LAST_HISTORY_ID_FILE, 'w') as f:
        f.write(str(history_id))


def get_gmail_service():
    SCOPES = ['https://mail.google.com/']
    creds = service_account.Credentials.from_service_account_file(
        settings.GMAIL_SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
        subject="info@easygoshuttle.com.au"
    )
    return build('gmail', 'v1', credentials=creds)


def get_email_body(payload):
    import base64
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        data = payload['body'].get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8')
    return ''


def get_thread_history(service, thread_id, max_messages=3):
    thread = service.users().threads().get(
        userId='me',
        id=thread_id,
        format='full'
    ).execute()
    
    messages = thread.get('messages', [])[-max_messages:]
    
    history = []
    for msg in messages:
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        body = get_email_body(msg['payload'])
        history.append({
            'from': headers.get('From', ''),
            'date': headers.get('Date', ''),
            'subject': headers.get('Subject', ''),
            'body': body
        })
    return history


@shared_task
def gmail_watch_topic(payload):
    service = get_gmail_service()
    
    history_id = payload.get('historyId')
    print(f"Received historyId: {history_id}")
    
    if not history_id:
        return

    start_history_id = get_last_history_id()
    if not start_history_id:
        start_history_id = str(int(history_id) - 10)

    try:
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded'],
        ).execute()

        print(f"History response: {history_response}")

        messages = []
        for record in history_response.get('history', []):
            for msg in record.get('messagesAdded', []):
                messages.append(msg['message']['id'])

        print(f"Found {len(messages)} new messages")

        save_last_history_id(history_id)

        for msg_id in messages:
            email = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            thread_id = email['threadId']
            headers = {h['name']: h['value'] for h in email['payload']['headers']}

            sender = headers.get('From', '')
            subject = headers.get('Subject', '')
            body = get_email_body(email['payload'])

            history_msgs = get_thread_history(service, thread_id)

            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print(f"Body: {body[:200]}")
            print(f"Thread history: {len(history_msgs)} messages")

    except Exception as e:
        print(f"Error: {e}")