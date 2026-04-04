import requests
from django.conf import settings
from posting_agent.review_manager import get_credentials


def post_to_google_business(text, call_to_action_url=None, image_url=None):
    creds = get_credentials()
    account_name = settings.GMB_ACCOUNT_NAME
    location_name = settings.GMB_LOCATION_NAME

    url = f"https://mybusiness.googleapis.com/v4/{account_name}/{location_name}/localPosts"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }

    body = {
        "languageCode": "en-US",
        "summary": text,
        "topicType": "STANDARD",
    }

    if call_to_action_url:
        body["callToAction"] = {
            "actionType": "LEARN_MORE",
            "url": call_to_action_url
        }

    if image_url:
        body["media"] = [{
            "mediaFormat": "PHOTO",
            "sourceUrl": image_url
        }]

    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 200:
        print(f"[GMB] ✅ 포스트 발행 완료!")
        return True
    else:
        print(f"[GMB] ❌ 실패: {response.status_code} {response.text}")
        return False