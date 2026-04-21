import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BIRD_API_BASE = 'https://api.bird.com'


def _format_e164(phone):
    if not phone:
        return None
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+'):
        return phone
    if phone.startswith('0'):
        return '+61' + phone[1:]
    return '+' + phone


def _bird_headers():
    return {
        'Authorization': f'AccessKey {settings.BIRD_API_KEY}',
        'Content-Type': 'application/json',
    }


def send_bird_sms(to_number, body):
    """Bird SMS API로 메시지 발송."""
    url = f'{BIRD_API_BASE}/workspaces/{settings.BIRD_WORKSPACE_ID}/channels/{settings.BIRD_CHANNEL_ID}/messages'
    payload = {
        'receiver': {'contacts': [{'identifierKey': 'phonenumber', 'identifierValue': to_number}]},
        'body': {'type': 'text', 'text': {'text': body}},
    }
    resp = requests.post(url, json=payload, headers=_bird_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def create_bird_mapping(instance):
    """트립 생성 시 고객↔드라이버 양방향 PhoneMapping 저장."""
    from blog.models import PhoneMapping, Post

    driver = instance.driver
    if not driver or not driver.driver_contact:
        logger.warning('[Bird] Post %s: driver or driver_contact missing, skipping.', instance.id)
        return False

    customer_phone = _format_e164(instance.contact)
    driver_phone = _format_e164(driver.driver_contact)

    if not customer_phone or not driver_phone:
        logger.warning(
            '[Bird] Post %s: invalid phone numbers. customer=%r driver=%r',
            instance.id, instance.contact, driver.driver_contact,
        )
        return False

    # 손님번호 → 드라이버번호 단방향만 관리 (이전 매핑 교체)
    # 드라이버 → 손님 연결은 bird_webhooks._get_driver_target() 에서 Post 모델 직접 조회
    PhoneMapping.objects.filter(from_number=customer_phone).delete()

    PhoneMapping.objects.create(from_number=customer_phone, to_number=driver_phone)
    Post.objects.filter(pk=instance.pk).update(use_proxy=True)

    logger.info('[Bird] Post %s: mapping created. customer=%s → driver=%s', instance.id, customer_phone, driver_phone)
    return True


def close_bird_mapping(instance):
    """트립 종료 시 PhoneMapping 삭제."""
    from blog.models import PhoneMapping, Post

    driver = instance.driver
    customer_phone = _format_e164(getattr(instance, 'contact', None))
    driver_phone = _format_e164(driver.driver_contact if driver else None)

    numbers = [n for n in [customer_phone, driver_phone] if n]
    if not numbers:
        logger.info('[Bird] Post %s: no phone numbers found, nothing to delete.', instance.id)
        return True

    deleted, _ = PhoneMapping.objects.filter(from_number__in=numbers).delete()
    if deleted > 0:
        Post.objects.filter(pk=instance.pk).update(use_proxy=False)
    logger.info('[Bird] Post %s: %d mappings deleted.', instance.id, deleted)
    return True
