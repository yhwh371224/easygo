import requests
from django.conf import settings


def post_to_facebook(text: str, image_bytes: bytes) -> bool:
    """Facebook Page에 이미지 + 글 포스팅"""
    try:
        # 1단계: 이미지 업로드
        upload_res = requests.post(
            f"https://graph.facebook.com/v19.0/{settings.FACEBOOK_PAGE_ID}/photos",
            params={"access_token": settings.FACEBOOK_PAGE_TOKEN},
            files={"source": ("post.jpg", image_bytes, "image/jpeg")},
            data={"caption": text, "published": "true"},
        )
        upload_res.raise_for_status()
        return True
    except Exception as e:
        print(f"Facebook 포스팅 실패: {e}")
        return False


def post_to_instagram(text: str, image_url: str) -> bool:
    """Instagram Business에 포스팅 (이미지 URL 필요)"""
    try:
        # 1단계: 미디어 컨테이너 생성
        container_res = requests.post(
            f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_ACCOUNT_ID}/media",
            params={"access_token": settings.FACEBOOK_PAGE_TOKEN},
            data={"image_url": image_url, "caption": text},
        )
        container_id = container_res.json().get("id")

        # 2단계: 발행
        publish_res = requests.post(
            f"https://graph.facebook.com/v19.0/{settings.INSTAGRAM_ACCOUNT_ID}/media_publish",
            params={"access_token": settings.FACEBOOK_PAGE_TOKEN},
            data={"creation_id": container_id},
        )
        publish_res.raise_for_status()
        return True
    except Exception as e:
        print(f"Instagram 포스팅 실패: {e}")
        return False
