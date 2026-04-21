import logging
import requests

from django.conf import settings
from django.db import transaction

from sms_utils import normalize_phone

logger = logging.getLogger(__name__)

BIRD_API_BASE = "https://api.bird.com"


# =========================
# Headers
# =========================
def _bird_headers():
    return {
        "Authorization": f"AccessKey {settings.BIRD_API_KEY}",
        "Content-Type": "application/json",
    }


# =========================
# Send SMS via Bird
# =========================
def send_bird_sms(to_number, body):
    """
    Send SMS using Bird API.
    Returns response JSON or None.
    """

    if not to_number or not body:
        logger.error("[Bird SMS] Invalid input to=%s body_empty=%s", to_number, not body)
        return None

    url = (
        f"{BIRD_API_BASE}/workspaces/"
        f"{settings.BIRD_WORKSPACE_ID}/channels/"
        f"{settings.BIRD_CHANNEL_ID}/messages"
    )

    payload = {
        "receiver": {
            "contacts": [
                {
                    "identifierKey": "phonenumber",
                    "identifierValue": to_number,
                }
            ]
        },
        "body": {
            "type": "text",
            "text": {"text": body},
        },
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=_bird_headers(),
            timeout=10,
        )

        # ❗ 실패 응답도 명확하게 기록
        if not resp.ok:
            logger.error(
                "[Bird SMS FAILED] to=%s status=%s response=%s",
                to_number,
                resp.status_code,
                resp.text,
            )
            return None

        logger.info("[Bird SMS SENT] to=%s", to_number)
        return resp.json()

    except requests.RequestException as e:
        logger.error(
            "[Bird SMS ERROR] to=%s error=%s",
            to_number,
            str(e),
        )
        return None


# =========================
# Create Proxy Mapping (Trip Start)
# =========================
def create_bird_mapping(instance):
    """
    Create one-way mapping:
    Customer → Driver
    """

    from blog.models import PhoneMapping, Post

    driver = instance.driver

    if not driver or not driver.driver_contact:
        logger.warning(
            "[Bird] Missing driver for post=%s",
            instance.id,
        )
        return False

    # ✅ ONLY ONE SOURCE OF TRUTH
    customer_phone = normalize_phone(instance.contact)
    driver_phone = normalize_phone(driver.driver_contact)

    if not customer_phone or not driver_phone:
        logger.warning(
            "[Bird] Invalid phone post=%s customer=%s driver=%s",
            instance.id,
            instance.contact,
            driver.driver_contact,
        )
        return False

    try:
        with transaction.atomic():
            # 기존 mapping 제거
            PhoneMapping.objects.filter(
                from_number=customer_phone
            ).delete()

            # 새 mapping 생성
            PhoneMapping.objects.create(
                from_number=customer_phone,
                to_number=driver_phone,
            )

            # proxy 활성화
            Post.objects.filter(pk=instance.pk).update(
                use_proxy=True
            )

        logger.info(
            "[Bird] Mapping created post=%s customer=%s → driver=%s",
            instance.id,
            customer_phone,
            driver_phone,
        )

        return True

    except Exception as e:
        logger.error(
            "[Bird] Mapping ERROR post=%s error=%s",
            instance.id,
            str(e),
        )
        return False


# =========================
# Close Proxy Mapping (Trip End)
# =========================
def close_bird_mapping(instance):
    """
    Remove mapping + disable proxy
    """

    from blog.models import PhoneMapping, Post

    customer_phone = normalize_phone(
        getattr(instance, "contact", None)
    )

    if not customer_phone:
        logger.info(
            "[Bird] No customer phone post=%s",
            instance.id,
        )
        Post.objects.filter(pk=instance.pk).update(
            use_proxy=False
        )
        return True

    try:
        deleted, _ = PhoneMapping.objects.filter(
            from_number=customer_phone
        ).delete()

        Post.objects.filter(pk=instance.pk).update(
            use_proxy=False
        )

        logger.info(
            "[Bird] Mapping closed post=%s deleted=%s",
            instance.id,
            deleted,
        )

        return True

    except Exception as e:
        logger.error(
            "[Bird] Close mapping ERROR post=%s error=%s",
            instance.id,
            str(e),
        )
        return False