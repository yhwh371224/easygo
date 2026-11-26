"""주유 기록 — 드라이버 텔레그램 봇 메시지 처리, 연비 계산, 은행 거래 대조.

메시지 형식 (드라이버 봇에 보내기):
    673156 52.83 136.78                 주행거리 km, 리터, 금액 $ (가득 주유)
    673156 52.83 136.78 BP Forestville  뒤의 글은 메모
    p 673500 20 52                      p = 가득 아님(partial)
    undo / cancel / 취소                 방금 보낸 기록 삭제(24시간 이내)
    fuel / /fuel                         사용법

연비는 '가득 → 가득' 방식: 직전 가득 주유 이후 달린 거리 ÷ 그 사이(이번 포함)에
넣은 리터 합. 직전 가득 주유 때 넣은 리터는 그 이전 구간 몫이라 빠진다.

AI 는 쓰지 않는다 — 정규식으로 숫자만 읽는다.
"""

import re
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone

FUEL_RE = re.compile(
    r'^(?:(?P<partial>p)\s+)?'
    r'(?P<odo>\d{1,3}(?:,\d{3})+|\d+)\s+'
    r'(?P<litres>\d+(?:\.\d+)?)\s*[lL]?\s+'
    r'\$?(?P<amount>\d+(?:\.\d{1,2})?)'
    r'(?:\s+(?P<notes>.+))?$',
    re.IGNORECASE | re.DOTALL,
)
UNDO_WORDS = {'undo', 'cancel', '취소', '/undo'}
HELP_WORDS = {'fuel', '/fuel'}

# 오타를 걸러내는 범위. 넘으면 저장하지 않고 다시 확인해 달라고 답한다.
# 범위를 벗어나는 진짜 기록은 Admin 에서 직접 넣는다.
MIN_LITRES = Decimal('1')
MAX_LITRES = Decimal('100')        # Hiace 탱크 70L, 여유 포함
MIN_PRICE_PER_L = Decimal('1.00')
MAX_PRICE_PER_L = Decimal('4.00')
MAX_KM_BETWEEN_FILLS = 3000
UNDO_WINDOW = timedelta(hours=24)
BANK_MATCH_DAYS = 10               # 은행 반영은 결제 후 며칠 늦게 들어온다

HELP_TEXT = (
    "⛽ Fuel log — send: odometer litres amount\n"
    "e.g. 673156 52.83 136.78\n"
    "Add a note after: 673156 52.83 136.78 BP Forestville\n"
    "Not a full tank? Start with p: p 673500 20 52\n"
    "Wrong entry? Send: undo"
)


def is_fuel_message(text):
    t = (text or '').strip()
    return bool(FUEL_RE.match(t)) or t.lower() in UNDO_WORDS | HELP_WORDS


def _q(value, places='0.01'):
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def economy_for(log):
    """이 기록에서 끝나는 '가득 → 가득' 구간. 계산할 수 없으면 None."""
    from fleet.models import FuelLog

    if not log.full_tank:
        return None
    prev_full = (FuelLog.objects
                 .filter(vehicle_id=log.vehicle_id, full_tank=True, odometer_km__lt=log.odometer_km)
                 .order_by('-odometer_km').first())
    if prev_full is None:
        return None
    segment = FuelLog.objects.filter(
        vehicle_id=log.vehicle_id,
        odometer_km__gt=prev_full.odometer_km, odometer_km__lte=log.odometer_km,
    ).aggregate(litres=Sum('litres'), amount=Sum('amount'))
    distance = log.odometer_km - prev_full.odometer_km
    litres = _q(segment['litres'] or 0)
    if distance <= 0 or litres <= 0:
        return None
    return {
        'distance_km': distance,
        'litres': litres,
        'km_per_l': _q(Decimal(distance) / litres, '0.1'),
        'l_per_100km': _q(litres * 100 / Decimal(distance), '0.1'),
        'cost_per_km': _q((segment['amount'] or 0) / Decimal(distance), '0.01'),
    }


def refresh_stored_values(vehicle_id):
    """그 차의 모든 주유 기록에 $/L, km/L, $/km 를 다시 계산해 저장한다.

    중간 기록을 고치거나 지우면 뒤 구간 값도 바뀌므로 차 단위로 전부 다시 맞춘다.
    차 한 대 기록은 많아야 수백 건이라 매번 전부 계산해도 된다.
    """
    from fleet.models import FuelLog

    for log in FuelLog.objects.filter(vehicle_id=vehicle_id):
        ppl = _q(log.amount / log.litres, '0.001') if log.litres else None
        eco = economy_for(log)
        values = {
            'distance_km': eco['distance_km'] if eco else None,
            'price_per_litre': ppl,
            'km_per_l': eco['km_per_l'] if eco else None,
            'cost_per_km': eco['cost_per_km'] if eco else None,
        }
        if any(getattr(log, k) != v for k, v in values.items()):
            FuelLog.objects.filter(pk=log.pk).update(**values)


def match_bank_transactions(logs=None):
    """은행에서 들어온 주유 거래(category=fuel)를 같은 금액의 주유 기록에 연결한다.

    은행 반영일은 결제일보다 늦으므로 [주유일, 주유일+10일] 안에서 가장 이른 거래를
    고른다. 이미 연결된 거래/기록은 건너뛴다. 연결한 개수를 돌려준다.
    """
    from accounting.models import Transaction
    from fleet.models import FuelLog

    if logs is None:
        since = timezone.localdate() - timedelta(days=90)
        logs = FuelLog.objects.filter(bank_transaction__isnull=True, date__gte=since)
    matched = 0
    for log in logs:
        if log.bank_transaction_id:
            continue
        tx = (Transaction.objects
              .filter(category='fuel', direction='expense', gross_amount=log.amount,
                      date__gte=log.date, date__lte=log.date + timedelta(days=BANK_MATCH_DAYS),
                      fuel_log__isnull=True)
              .order_by('date', 'pk').first())
        if tx:
            FuelLog.objects.filter(pk=log.pk).update(bank_transaction=tx)
            log.bank_transaction = tx
            matched += 1
    return matched


def handle_driver_message(driver, text):
    """드라이버 봇 메시지 하나를 처리하고 답장 문구를 돌려준다."""
    t = (text or '').strip()
    low = t.lower()
    if low in HELP_WORDS:
        return HELP_TEXT
    if low in UNDO_WORDS:
        return _undo(driver)
    m = FUEL_RE.match(t)
    if not m:
        return HELP_TEXT
    return _record(driver, m)


def _pick_vehicle(driver):
    vehicles = list(driver.vehicles.filter(is_active=True))
    if len(vehicles) == 1:
        return vehicles[0], None
    if not vehicles:
        return None, "No vehicle is assigned to you, so I couldn't save this. Please tell the office."
    return None, "More than one vehicle is assigned to you, so I couldn't save this. Please tell the office."


def _record(driver, m):
    from fleet.models import FuelLog, Vehicle

    odo = int(m['odo'].replace(',', ''))
    litres = _q(m['litres'])
    amount = _q(m['amount'])
    full = not m['partial']
    notes = (m['notes'] or '').strip()

    vehicle, error = _pick_vehicle(driver)
    if error:
        return error
    if not (MIN_LITRES <= litres <= MAX_LITRES):
        return f"⚠️ {litres} L looks wrong. Not saved — please check and send again."
    ppl = amount / litres
    if not (MIN_PRICE_PER_L <= ppl <= MAX_PRICE_PER_L):
        return (f"⚠️ ${amount} for {litres} L is ${_q(ppl, '0.001')}/L, which looks wrong. "
                "Not saved — check the order: odometer litres amount.")

    with db_transaction.atomic():
        vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
        last = FuelLog.objects.filter(vehicle=vehicle).order_by('-odometer_km').first()
        if last and odo <= last.odometer_km:
            return (f"⚠️ Odometer {odo:,} km is not more than the last fuel log "
                    f"({last.odometer_km:,} km on {last.date:%d/%m}). Not saved.")
        if last and odo - last.odometer_km > MAX_KM_BETWEEN_FILLS:
            return (f"⚠️ {odo - last.odometer_km:,} km since the last fuel log "
                    f"({last.odometer_km:,} km) looks too far. Not saved — please check.")
        if last is None and vehicle.odometer_km and odo < vehicle.odometer_km:
            return (f"⚠️ Odometer {odo:,} km is less than the vehicle's recorded "
                    f"{vehicle.odometer_km:,} km. Not saved.")
        log = FuelLog.objects.create(
            vehicle=vehicle, date=timezone.localdate(), odometer_km=odo, litres=litres,
            amount=amount, full_tank=full, notes=notes, driver=driver,
            source=FuelLog.SOURCE_TELEGRAM,
        )
        if vehicle.odometer_km is None or odo > vehicle.odometer_km:
            Vehicle.objects.filter(pk=vehicle.pk).update(odometer_km=odo)
        refresh_stored_values(vehicle.pk)

    log.refresh_from_db()
    match_bank_transactions([log])
    return _saved_reply(vehicle, log)


def _saved_reply(vehicle, log):
    lines = [f"⛽ Saved — {vehicle.make_model} ({vehicle.plate_number}), {log.date:%d/%m/%Y}"]
    lines.append(f"{log.odometer_km:,} km · {log.litres} L · ${log.amount}"
                 + ("" if log.full_tank else " · partial"))
    eco = economy_for(log)
    if eco:
        lines.append(f"{eco['distance_km']:,} km / {eco['litres']} L → "
                     f"{log.km_per_l} km/L ({eco['l_per_100km']} L/100km)")
        lines.append(f"${log.price_per_litre}/L · ${log.cost_per_km}/km")
    else:
        lines.append(f"${log.price_per_litre}/L")
        if log.full_tank:
            lines.append("Economy will show from the next full tank.")
        else:
            lines.append("Partial fill — counted in the next full tank.")
    if vehicle.next_service_km:
        left = vehicle.next_service_km - log.odometer_km
        if left > 0:
            lines.append(f"🔧 Next service in {left:,} km ({vehicle.next_service_km:,})")
        else:
            lines.append(f"🔧 Service overdue by {-left:,} km ({vehicle.next_service_km:,})")
    lines.append("Wrong? Send: undo")
    return '\n'.join(lines)


def _undo(driver):
    from fleet.models import FuelLog, Vehicle

    cutoff = timezone.now() - UNDO_WINDOW
    with db_transaction.atomic():
        log = (FuelLog.objects.select_for_update()
               .filter(driver=driver, source=FuelLog.SOURCE_TELEGRAM, created_at__gte=cutoff)
               .order_by('-created_at').first())
        if log is None:
            return "Nothing to undo (only entries from the last 24 hours can be undone here)."
        vehicle = Vehicle.objects.select_for_update().get(pk=log.vehicle_id)
        desc = f"{log.odometer_km:,} km · {log.litres} L · ${log.amount}"
        odo = log.odometer_km
        log.delete()
        if vehicle.odometer_km == odo:
            prev = FuelLog.objects.filter(vehicle=vehicle).order_by('-odometer_km').first()
            if prev:
                Vehicle.objects.filter(pk=vehicle.pk).update(odometer_km=prev.odometer_km)
        refresh_stored_values(vehicle.pk)
    return f"🗑 Deleted: {desc}"
