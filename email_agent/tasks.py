from celery import shared_task
from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.conf import settings
from .email_ai import analyze_email_with_claude
from .price_utils import calculate_pickup_time, calculate_price
import os


LAST_HISTORY_ID_FILE = '/home/horeb/github/easygo/last_history_id.txt'


def get_last_history_id():
    if os.path.exists(LAST_HISTORY_ID_FILE):
        with open(LAST_HISTORY_ID_FILE, 'r') as f:
            return f.read().strip()
    return None


def save_last_history_id(history_id):
    current = get_last_history_id()
    if not current or int(history_id) > int(current):
        with open(LAST_HISTORY_ID_FILE, 'w') as f:
            f.write(str(history_id))
        return True
    return False


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
    if not history_id:
        return

    start_history_id = get_last_history_id()
    if not start_history_id:
        start_history_id = str(int(history_id) - 10)

    if int(history_id) <= int(start_history_id):
        print(f"Already processed historyId: {history_id}, skipping")
        return

    if not save_last_history_id(history_id):
        print(f"historyId {history_id} already being processed, skipping")
        return

    try:
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded'],
        ).execute()

        messages = []
        for record in history_response.get('history', []):
            for msg in record.get('messagesAdded', []):
                messages.append(msg['message']['id'])

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
            thread_history = get_thread_history(service, thread_id)

            print(f"From: {sender}")
            print(f"Subject: {subject}")

            # Claude API 호출
            result = analyze_email_with_claude(sender, subject, body, thread_history)

            print(f"Email type: {result['email_type']}")
            print(f"Extracted: {result['extracted_info']}")
            print(f"Has enough info: {result['has_enough_info']}")
            print(f"Missing: {result['missing_fields']}")
            print(f"Reply draft: {result['suggested_reply'][:300]}")

            # 가격문의이고 정보 충분하면 가격 계산
            if result['email_type'] == 'price_inquiry' and result['has_enough_info']:
                info = result['extracted_info']

                pickup_time = calculate_pickup_time(
                    direction=info['direction'],
                    flight_time=info.get('flight_time'),
                    pickup_time=info.get('pickup_time')
                )

                price = calculate_price(
                    suburb_name=info['suburb'],
                    passengers=info['passengers'],
                    direction=info['direction'],
                    large_luggage=info.get('large_luggage') or 0,
                    medium_small_luggage=info.get('medium_small_luggage') or 0
                )

                print(f"Pickup time: {pickup_time}")
                print(f"Price: ${price}")

    except Exception as e:
        print(f"Error: {e}")