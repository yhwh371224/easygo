import logging
import requests

from django.conf import settings
from django.db import transaction

from blog.sms_utils import normalize_phone, is_au_mobile

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
def send_bird_sms(to_number, body, channel_id=None):
    """
    Send SMS using Bird API.

    The channel decides which number the text comes from, so replies in a proxy
    session must go back out on the channel the message arrived on — otherwise
    the customer is answered from a number they were never given.
    Returns response JSON or None.
    """

    if not to_number or not body:
        logger.error("[Bird SMS] Invalid input to=%s body_empty=%s", to_number, not body)
        return None

    channel_id = channel_id or settings.BIRD_CHANNEL_ID

    url = (
        f"{BIRD_API_BASE}/workspaces/"
        f"{settings.BIRD_WORKSPACE_ID}/channels/"
        f"{channel_id}/messages"
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

        logger.info("[Bird SMS SENT] to=%s channel=%s", to_number, channel_id)
        return resp.json()

    except requests.RequestException as e:
        logger.error(
            "[Bird SMS ERROR] to=%s error=%s",
            to_number,
            str(e),
        )
        return None


# =========================
# Resolve Proxy Number (Display)
# =========================
def resolve_virtual_number(driver):
    """
    The number to advertise for this driver: their own virtual number when Bird
    actually routes it to us, otherwise the shared company number.

    Every surface — customer email, calendar, driver dashboard — must resolve
    through here. Two surfaces each deriving a number their own way is what put
    a driver and a customer on different numbers and left them unable to
    connect; going through one function makes that mismatch impossible.
    """

    virtual_number = getattr(driver, "virtual_number", None)

    if virtual_number and virtual_number.is_wired:
        return virtual_number.number

    if virtual_number:
        logger.warning(
            "[Bird] virtual_number %s is assigned to driver=%s but has no Bird "
            "channels — advertising %s instead. Run sync_bird_channels.",
            virtual_number.number,
            getattr(driver, "id", None),
            settings.BIRD_NUMBER,
        )

    return settings.BIRD_NUMBER


def get_proxy_number(instance, driver=None):
    """
    The number the customer should call/text for this booking, or None when the
    booking has no live proxy session and callers should show the real contact.
    """

    from blog.models import PhoneMapping
    from utils.prepay_helper import is_foreign_number

    if not getattr(instance, "use_proxy", False):
        return None

    if driver is None:
        driver = getattr(instance, "driver", None)

    if driver is None:
        return None

    # Our numbers are AU landline-style; an overseas customer can't reliably
    # reach them, so both sides fall back to the real contact.
    if is_foreign_number(getattr(instance, "contact", None)):
        return None

    customer_phone = normalize_phone(getattr(instance, "contact", None))
    if not customer_phone:
        return None

    # Only AU mobiles (04… / +61 4…) get a proxy — landlines can't be reliably
    # bridged/texted on our Bird numbers, so they show the real contact instead.
    if not is_au_mobile(customer_phone):
        return None

    if not PhoneMapping.objects.filter(from_number=customer_phone).exists():
        return None

    return resolve_virtual_number(driver)


# =========================
# Create Proxy Mapping (Trip Start)
# =========================
def create_bird_mapping(instance):
    """
    Open a proxy session: an inbound leg from this customer reaches this driver.

    Routing is keyed on the caller, not on the number dialled, so a driver
    without a virtual number of their own still gets a working session on the
    shared company number — resolve_virtual_number() decides which number the
    two sides are told to use.
    """

    from blog.models import PhoneMapping, Post

    driver = instance.driver

    if not driver or not driver.driver_contact:
        logger.warning(
            "[Bird] Missing driver for post=%s",
            instance.id,
        )
        return False

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

    # Only AU mobiles (04… / +61 4…) get a proxy session — a landline customer
    # can't be bridged/texted on our Bird numbers, so no mapping is opened.
    if not is_au_mobile(customer_phone):
        logger.info(
            "[Bird] Skipping proxy — customer %s is not an AU mobile (post=%s)",
            customer_phone,
            instance.id,
        )
        return False

    virtual_number = resolve_virtual_number(driver)

    try:
        with transaction.atomic():
            PhoneMapping.objects.filter(from_number=customer_phone).delete()

            PhoneMapping.objects.create(
                from_number=customer_phone,
                to_number=driver_phone,
                driver_name=driver.driver_name,
                pickup_date=instance.pickup_date,
                pickup_time=instance.pickup_time,
            )

            Post.objects.filter(pk=instance.pk).update(use_proxy=True)

        logger.info(
            "[Bird] Mapping created post=%s customer=%s → virtual=%s (driver=%s)",
            instance.id,
            customer_phone,
            virtual_number,
            driver.id,
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
        with transaction.atomic():  # ← 추가
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