import logging

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from decouple import config

logger = logging.getLogger(__name__)

account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
proxy_service_sid = config('TWILIO_PROXY_SERVICE_SID')

client = Client(account_sid, auth_token)


def _format_e164(phone):
    """Australian number → E.164. Already E.164 numbers pass through unchanged."""
    if not phone:
        return None
    phone = phone.strip()
    if phone.startswith('+'):
        return phone
    if phone.startswith('0'):
        return '+61' + phone[1:]
    return '+' + phone


def _delete_twilio_session(session_sid):
    """Twilio 세션 삭제. 이미 없는 세션(404)은 정상 처리."""
    try:
        client.proxy.v1.services(proxy_service_sid).sessions(session_sid).delete()
    except TwilioRestException as e:
        if e.status != 404:
            raise


def create_proxy_session(instance):
    """Twilio Proxy 세션 생성.

    - instance.proxy_number          ← 고객이 드라이버에게 전화할 때 쓰는 번호 (이메일에 표시)
    - instance.customer_proxy_number ← 드라이버가 고객에게 전화할 때 쓰는 번호 (run sheet에 표시)
    - instance.proxy_session_sid     ← 세션 종료용 SID

    성공 시 True, 실패 시 False 반환.
    """
    driver = instance.driver
    if not driver or not driver.driver_contact:
        logger.warning(f"[Proxy] Post {instance.id}: driver or driver_contact missing, skipping.")
        return False

    customer_phone = _format_e164(instance.contact)
    driver_phone = _format_e164(driver.driver_contact)

    if not customer_phone or not driver_phone:
        logger.warning(
            f"[Proxy] Post {instance.id}: invalid phone number(s). "
            f"customer={instance.contact} driver={driver.driver_contact}"
        )
        return False

    session = None
    try:
        session = client.proxy.v1.services(proxy_service_sid).sessions.create(
            unique_name=f"booking-{instance.id}"
        )

        # 참가자 추가 도중 실패하면 except 블록에서 세션을 즉시 삭제해 고아 세션 방지
        customer_participant = (
            client.proxy.v1.services(proxy_service_sid)
            .sessions(session.sid)
            .participants.create(
                identifier=customer_phone,
                friendly_name=instance.name or "Customer",
            )
        )

        driver_participant = (
            client.proxy.v1.services(proxy_service_sid)
            .sessions(session.sid)
            .participants.create(
                identifier=driver_phone,
                friendly_name=driver.driver_name or "Driver",
            )
        )

        # proxy_identifier: Twilio가 상대방에게 노출하는 가상번호
        # None이면 번호 풀 부족 등의 문제 → 세션 정리 후 실패 처리
        customer_proxy = customer_participant.proxy_identifier  # 드라이버 run sheet에 표시
        driver_proxy = driver_participant.proxy_identifier      # 고객 이메일에 표시

        if not customer_proxy or not driver_proxy:
            raise ValueError(
                f"Twilio returned empty proxy_identifier — "
                f"number pool may be exhausted. "
                f"customer_proxy={customer_proxy!r} driver_proxy={driver_proxy!r}"
            )

        model_class = type(instance)
        model_class.objects.filter(pk=instance.pk).update(
            proxy_session_sid=session.sid,
            proxy_number=driver_proxy,
            customer_proxy_number=customer_proxy,
        )

        logger.info(
            f"[Proxy] Post {instance.id}: session {session.sid} created. "
            f"driver_proxy={driver_proxy} customer_proxy={customer_proxy}"
        )
        return True

    except Exception as e:
        # 세션이 생성됐지만 이후 단계에서 실패 → Twilio에서 고아 세션 삭제
        if session is not None:
            try:
                _delete_twilio_session(session.sid)
                logger.info(f"[Proxy] Post {instance.id}: orphan session {session.sid} cleaned up.")
            except Exception as cleanup_err:
                logger.error(
                    f"[Proxy] Post {instance.id}: failed to clean up orphan session {session.sid} — "
                    f"{cleanup_err}. Manual deletion required on Twilio console."
                )
        logger.error(f"[Proxy] Post {instance.id}: create_proxy_session failed — {e}")
        return False


def close_proxy_session(instance):
    """Twilio Proxy 세션 종료 및 proxy 번호 초기화.

    성공 시 True, 실패 시 False 반환.
    이미 삭제된 세션(404)은 성공으로 처리하고 DB를 정리한다.
    """
    session_sid = instance.proxy_session_sid
    if not session_sid:
        logger.info(f"[Proxy] Post {instance.id}: no proxy_session_sid, nothing to close.")
        return True

    try:
        _delete_twilio_session(session_sid)  # 404면 예외 없이 통과

        model_class = type(instance)
        model_class.objects.filter(pk=instance.pk).update(
            proxy_session_sid='',
            proxy_number='',
            customer_proxy_number='',
        )

        logger.info(f"[Proxy] Post {instance.id}: session {session_sid} closed.")
        return True

    except Exception as e:
        logger.error(f"[Proxy] Post {instance.id}: close_proxy_session failed — {e}")
        return False
