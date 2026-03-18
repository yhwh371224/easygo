import re
import base64
import os

from celery import shared_task
from googleapiclient.discovery import build
from google.oauth2 import service_account
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings
from .email_ai import analyze_email_with_claude


LAST_HISTORY_ID_FILE = '/home/horeb/github/easygo/last_history_id.txt'
PROCESSED_LABEL_ID = 'Label_956123326350558597'

EMAIL_SIGNATURE = """
<br>
<div style="font-family: Arial, sans-serif; color: #555; line-height: 1.1;">
<p style="font-size: 12px; margin: 2px 0;"><strong>EasyGo Airport Shuttle Team</strong></p>
</div>
"""

def is_message_processed(service, msg_id):
    email = service.users().messages().get(
        userId='me',
        id=msg_id,
        format='metadata',
        metadataHeaders=['labelIds']
    ).execute()
    return PROCESSED_LABEL_ID in email.get('labelIds', [])


def mark_message_processed(service, msg_id):
    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={'addLabelIds': [PROCESSED_LABEL_ID]}
    ).execute()


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


def create_gmail_draft(service, to, subject, body, thread_id=None):
    msg = MIMEMultipart('related')
    msg['to'] = to
    msg['subject'] = f"Re: {subject}" if subject else "Re: Your Inquiry"

    html_body = body.replace('\n', '<br>')
    
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
{html_body}
</body>
</html>
"""
    
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

    draft_body = {'message': {'raw': raw}}
    if thread_id:
        draft_body['message']['threadId'] = thread_id

    draft = service.users().drafts().create(
        userId='me',
        body=draft_body
    ).execute()

    print(f"Draft created: {draft['id']}")
    return draft['id']


@shared_task
def gmail_watch_topic(payload):
    service = get_gmail_service()

    history_id = payload.get('historyId')
    if not history_id:
        return
    history_id = str(history_id)

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

            current_labels = email.get('labelIds', [])
            if 'INBOX' not in current_labels:
                print(f"Skipping message {msg_id}: not in INBOX (labels: {current_labels})")
                continue

            thread_id = email['threadId']
            headers = {h['name']: h['value'] for h in email['payload']['headers']}

            sender = headers.get('From', '')
            subject = headers.get('Subject', '')

            # 이미 처리한 메시지 스킵
            if is_message_processed(service, msg_id):
                print(f"Already processed message {msg_id}, skipping")
                continue

            # 내가 보낸 이메일 스킵
            if 'info@easygoshuttle.com.au' in sender and '[New Contact] Submission from' not in subject:
                print(f"Skipping own email: {subject}")
                continue

            # 스팸/자동발송 스킵
            skip_senders = ['noreply', 'no-reply', 'mailer-daemon', 'postmaster', 'notifications']
            if any(skip in sender.lower() for skip in skip_senders):
                print(f"Skipping automated email: {sender}")
                continue
            
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

            reply_body = result['suggested_reply'] + EMAIL_SIGNATURE

            # Contact Form 이메일이면 본문에서 이메일 추출
            if '[New Contact] Submission from' in subject:
                match = re.search(r'email:\s*(\S+)', body)
                reply_to = match.group(1) if match else sender
            else:
                reply_to = sender

            # Gmail Draft 생성
            try:
                create_gmail_draft(service, reply_to, subject, reply_body, thread_id=thread_id)
                mark_message_processed(service, msg_id)
            except Exception as e:
                print(f"Draft creation failed for message {msg_id}: {e}")

    except Exception as e:
        print(f"Error: {e}")


