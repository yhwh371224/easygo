"""서비스(정비) 기록 — 드라이버 텔레그램 봇 메시지 처리.

메시지 형식 (드라이버 봇에 보내기, 맨 앞이 'service' 면 서비스 기록):
    service 674100 140 oil filter Penrite 10w40      셀프 서비스: 주행거리 km, 금액 $, 내용
    service 676000 503 @Ultra Tune Artarmon coolant leak fixed
                                                     @ 뒤는 정비소 (이전에 쓴 정비소 이름은
                                                     알아본다, 처음 쓰는 이름은 ':' 또는 ','
                                                     까지)
    service                                          사용법
    undo                                             주유/서비스 중 마지막 기록 삭제 (fleet.fuel)

항목 단어(oil, filter, air, tyre, brake, trans)는 ServiceItem 줄로 저장하고, 쓴 글은
전부 메모로 남긴다. 엔진오일이 있으면 차의 다음 서비스 = 주행거리 + 7,000 km.

AI 는 쓰지 않는다 — 정규식으로 읽는다.
"""

import re
from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

SERVICE_INTERVAL_KM = 7000
MAX_KM_FROM_VEHICLE = 3000     # 차에 기록된 주행거리와 이만큼 넘게 다르면 오타로 본다
MAX_AMOUNT = Decimal('20000')

SERVICE_WORD_RE = re.compile(r'^service\b', re.IGNORECASE)
SERVICE_RE = re.compile(
    r'^service\s+'
    r'(?P<odo>\d{1,3}(?:,\d{3})+|\d+)\s*(?:km)?\s+'
    r'\$?(?P<amount>\d+(?:\.\d{1,2})?)'
    r'(?:\s+(?P<rest>.+))?$',
    re.IGNORECASE | re.DOTALL,
)

HELP_TEXT = (
    "🔧 Service log — send: service odometer amount what-was-done\n"
    "e.g. service 674100 140 oil filter Penrite 10w40\n"
    "At a workshop, put @ before its name:\n"
    "service 676000 503 @Ultra Tune Artarmon: coolant leak fixed\n"
    "Item words: oil, filter, air, tyre, brake, trans\n"
    "Wrong entry? Send: undo"
)

_NOT_ENGINE_OIL = {'trans', 'transmission', 'diff', 'differential', 'gear', 'gearbox',
                   'steering', 'brake'}
_NOT_OIL_FILTER = {'air', 'fuel', 'cabin', 'pollen'}


def is_service_message(text):
    return bool(SERVICE_WORD_RE.match((text or '').strip()))


def parse_items(text):
    """메모 글에서 항목 종류를 순서대로 뽑는다 (중복 없이)."""
    from fleet.models import ServiceItem

    words = re.findall(r'[a-z]+', (text or '').lower())
    found = []

    def add(kind):
        if kind not in found:
            found.append(kind)

    for i, w in enumerate(words):
        prev = words[i - 1] if i else ''
        if w in ('trans', 'transmission'):
            add(ServiceItem.TRANSMISSION_OIL)
        elif w == 'air' and i + 1 < len(words) and words[i + 1] == 'filter':
            add(ServiceItem.AIR_FILTER)
        elif w in ('tyre', 'tyres', 'tire', 'tires'):
            add(ServiceItem.TYRE)
        elif w in ('brake', 'brakes'):
            add(ServiceItem.BRAKE_PAD)
        elif w == 'filter' and prev not in _NOT_OIL_FILTER:
            add(ServiceItem.OIL_FILTER)
        elif w == 'oil' and prev not in _NOT_ENGINE_OIL:
            add(ServiceItem.ENGINE_OIL)
    return found


def split_vendor(rest):
    """'@정비소 메모' → (vendor, notes). @ 가 없으면 ('', rest) = 셀프 서비스."""
    from fleet.models import ServiceVisit

    rest = (rest or '').strip()
    if not rest.startswith('@'):
        return '', rest
    body = rest[1:].strip()
    known = sorted(
        {v.strip() for v in ServiceVisit.objects.exclude(vendor='').values_list('vendor', flat=True)},
        key=len, reverse=True,
    )
    for name in known:
        if body.lower().startswith(name.lower()) and (
                len(body) == len(name) or not body[len(name)].isalnum()):
            return name, body[len(name):].lstrip(' :,-').strip()
    m = re.match(r'^([^:,]+)[:,]\s*(.*)$', body, re.DOTALL)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return body, ''


def handle_service_message(driver, text):
    t = (text or '').strip()
    m = SERVICE_RE.match(t)
    if not m:
        return HELP_TEXT
    return _record(driver, m)


def _record(driver, m):
    from fleet.fuel import _pick_vehicle, _q
    from fleet.models import ServiceItem, ServiceVisit, Vehicle

    odo = int(m['odo'].replace(',', ''))
    amount = _q(m['amount'])
    rest = (m['rest'] or '').strip()
    vendor, notes = split_vendor(rest)
    items = parse_items(notes if vendor else rest)

    vehicle, error = _pick_vehicle(driver)
    if error:
        return error
    if not (Decimal('0') < amount <= MAX_AMOUNT):
        return f"⚠️ ${amount} looks wrong. Not saved — please check and send again."

    with db_transaction.atomic():
        vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
        if vehicle.odometer_km and abs(odo - vehicle.odometer_km) > MAX_KM_FROM_VEHICLE:
            return (f"⚠️ Odometer {odo:,} km is far from the vehicle's recorded "
                    f"{vehicle.odometer_km:,} km. Not saved — please check.")
        visit = ServiceVisit.objects.create(
            vehicle=vehicle, service_date=timezone.localdate(), self_serviced=not vendor,
            vendor=vendor, odometer_km=odo, total_cost=amount, notes=notes if vendor else rest,
            driver=driver, source=ServiceVisit.SOURCE_TELEGRAM,
        )
        ServiceItem.objects.bulk_create([ServiceItem(visit=visit, service_type=k) for k in items])
        updates = {}
        replaced = {}
        if vehicle.odometer_km is None or odo > vehicle.odometer_km:
            replaced['replaced_odometer_km'] = vehicle.odometer_km
            updates['odometer_km'] = odo
        if ServiceItem.ENGINE_OIL in items:
            replaced['replaced_next_service_km'] = vehicle.next_service_km
            updates['next_service_km'] = odo + SERVICE_INTERVAL_KM
        if replaced:
            ServiceVisit.objects.filter(pk=visit.pk).update(**replaced)
        if updates:
            Vehicle.objects.filter(pk=vehicle.pk).update(**updates)
            for k, v in updates.items():
                setattr(vehicle, k, v)

    return _saved_reply(vehicle, visit, items)


def _saved_reply(vehicle, visit, items):
    from fleet.models import ServiceItem

    labels = dict(ServiceItem.SERVICE_TYPE_CHOICES)
    who = visit.vendor or 'Self serviced'
    lines = [f"🔧 Saved — {vehicle.make_model} ({vehicle.plate_number}), {visit.service_date:%d/%m/%Y}",
             f"{who} · {visit.odometer_km:,} km · ${visit.total_cost}"]
    lines += [f"• {labels[k]}" for k in items]
    if visit.notes:
        lines.append(f"Note: {visit.notes}")
    if vehicle.next_service_km:
        if ServiceItem.ENGINE_OIL in items:
            lines.append(f"Next service: {vehicle.next_service_km:,} km (in {SERVICE_INTERVAL_KM:,} km)")
        else:
            lines.append(f"Next service still: {vehicle.next_service_km:,} km")
    lines.append("Wrong? Send: undo")
    return '\n'.join(lines)


def undo_visit(visit):
    """텔레그램 서비스 기록 하나를 지우고 차 값(주행거리·다음 서비스)을 되돌린다."""
    from fleet.models import FuelLog, ServiceVisit, Vehicle

    vehicle = Vehicle.objects.select_for_update().get(pk=visit.vehicle_id)
    desc = f"{visit.vendor or 'Self serviced'} · {visit.odometer_km:,} km · ${visit.total_cost}"
    odo = visit.odometer_km
    had_engine_oil = visit.items.filter(service_type='engine_oil').exists()
    replaced_next = visit.replaced_next_service_km
    replaced_odo = visit.replaced_odometer_km
    visit.delete()
    updates = {}
    # 그 사이 다른 기록이 값을 바꿨으면 건드리지 않는다.
    if had_engine_oil and vehicle.next_service_km == (odo or 0) + SERVICE_INTERVAL_KM:
        updates['next_service_km'] = replaced_next
    if odo and vehicle.odometer_km == odo:
        last_fuel = FuelLog.objects.filter(vehicle=vehicle).order_by('-odometer_km').first()
        last_visit = (ServiceVisit.objects.filter(vehicle=vehicle, odometer_km__isnull=False)
                      .order_by('-odometer_km').first())
        candidates = [x.odometer_km for x in (last_fuel, last_visit) if x]
        if replaced_odo:
            candidates.append(replaced_odo)
        if candidates:
            updates['odometer_km'] = max(candidates)
    if updates:
        Vehicle.objects.filter(pk=vehicle.pk).update(**updates)
    return f"🗑 Deleted service: {desc}"
