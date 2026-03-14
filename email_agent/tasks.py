from celery import shared_task
from googleapiclient.discovery import build
from google.oauth2 import service_account
from django.conf import settings
from .email_ai import analyze_email_with_claude
from .price_utils import calculate_pickup_time, calculate_price
import base64
import os
from email.mime.text import MIMEText


LAST_HISTORY_ID_FILE = '/home/horeb/github/easygo/last_history_id.txt'
PROCESSED_MESSAGES_FILE = '/home/horeb/github/easygo/processed_messages.txt'


def is_message_processed(msg_id):
    if os.path.exists(PROCESSED_MESSAGES_FILE):
        with open(PROCESSED_MESSAGES_FILE, 'r') as f:
            return msg_id in f.read()
    return False


def mark_message_processed(msg_id):
    with open(PROCESSED_MESSAGES_FILE, 'a') as f:
        f.write(msg_id + '\n')


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


def create_gmail_draft(service, to, subject, body):
    """Gmail Draft 생성"""
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = f"Re: {subject}"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    draft = service.users().drafts().create(
        userId='me',
        body={'message': {'raw': raw}}
    ).execute()

    print(f"Draft created: {draft['id']}")
    return draft['id']


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
                if 'INBOX' in msg['message'].get('labelIds', []):
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

            # 이미 처리한 메시지 스킵
            if is_message_processed(msg_id):
                print(f"Already processed message {msg_id}, skipping")
                continue

            # 내가 보낸 이메일 스킵
            if 'info@easygoshuttle.com.au' in sender:
                print(f"Skipping own email: {subject}")
                continue

            # 처리 완료 표시
            mark_message_processed(msg_id)
            
            body = get_email_body(email['payload'])
            thread_history = get_thread_history(service, thread_id)

            print(f"From: {sender}")
            print(f"Subject: {subject}")

            # Claude API 호출
            try:
                result = analyze_email_with_claude(sender, subject, body, thread_history)

            except Exception as e:
                print(f"Claude API failed for message {msg_id}: {e}")
                continue

            if not result:
                print(f"Claude API returned empty for message {msg_id}")
                continue

            print(f"Email type: {result['email_type']}")
            print(f"Extracted: {result['extracted_info']}")
            print(f"Has enough info: {result['has_enough_info']}")
            print(f"Missing: {result['missing_fields']}")
            print(f"Reply draft: {result['suggested_reply'][:300]}")

            # 가격문의이고 정보 충분하면 가격 계산 후 suggested_reply에 가격 추가
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

                # 가격 정보를 reply에 추가
                reply_body = result['suggested_reply']
                if price:
                    reply_body += f"\n\nPickup Time: {pickup_time}\nTotal Price: ${price} AUD"

            else:
                reply_body = result['suggested_reply']

            # Gmail Draft 생성
            try:
                create_gmail_draft(service, sender, subject, reply_body)
            except Exception as e:
                print(f"Draft creation failed for message {msg_id}: {e}")

    except Exception as e:
        print(f"Error: {e}")
