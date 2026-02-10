import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from main.settings import RECIPIENT_EMAIL
from django.conf import settings


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
LABEL_NAME = "cash"
EXCLUDED_EMAILS = [
    "info@easygoshuttle.com.au",
    "info+canned.response@easygoshuttle.com.au",
]
SERVICE_ACCOUNT_FILE = settings.GMAIL_SERVICE_ACCOUNT_FILE 
DELEGATED_USER_EMAIL = RECIPIENT_EMAIL

# 이메일 주소 추출 정규식 (콤마, 세미콜론 등 여러 구분자 포함)
EMAIL_REGEX = re.compile(r'[\w\.\+\-]+@[\w\.-]+')


def extract_emails(header_value):
    """
    헤더 텍스트에서 모든 이메일 주소를 추출
    To 헤더에 여러 이메일이 있을 경우도 모두 처리
    """
    if not header_value:
        return []
    return EMAIL_REGEX.findall(header_value)


def get_label_id(service, label_name):
    """Gmail에서 라벨 이름으로 ID 반환"""
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    for label in labels:
        if label.get("name") == label_name:
            return label.get("id")
    print(f"Label '{label_name}' not found.")
    return None


def get_cash_emails(service):
    """cash 라벨이 붙은 메일에서 From/To 이메일을 모두 추출"""
    try:
        label_id = get_label_id(service, LABEL_NAME)
        if not label_id:
            return []

        # 메시지 목록 불러오기 (페이지네이션 포함)
        messages = []
        page_token = None
        while True:
            resp = service.users().messages().list(
                userId="me", labelIds=[label_id], pageToken=page_token
            ).execute()
            msgs = resp.get("messages", [])
            if msgs:
                messages.extend(msgs)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        if not messages:
            print("No messages found with the 'cash' label.")
            return []

        collected = set()
        excluded_lower = {e.lower() for e in EXCLUDED_EMAILS}

        for message in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=message["id"]
                ).execute()
            except HttpError as e:
                print(f"Failed to fetch message {message.get('id')}: {e}")
                continue

            headers = msg.get("payload", {}).get("headers", [])
            for header in headers:
                name = header.get("name", "").lower()
                if name in ("from", "to"):
                    emails = extract_emails(header.get("value", ""))
                    for email in emails:
                        elow = email.lower()
                        if elow and elow not in excluded_lower:
                            collected.add(elow)

        # 중복 제거 후 정렬하여 반환
        return sorted(collected)

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def main():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=DELEGATED_USER_EMAIL
    )
    try:
        service = build("gmail", "v1", credentials=credentials)
        return get_cash_emails(service)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


if __name__ == "__main__":
    cash_emails = main()
    print(cash_emails)