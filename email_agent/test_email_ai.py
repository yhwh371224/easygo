"""
테스트 실행 방법:
    python manage.py shell < email_agent/test_email_ai.py
또는
    cd 프로젝트 루트
    python -m pytest email_agent/test_email_ai.py -v  (pytest 설치 시)
"""

import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easygo.settings')
django.setup()

from email_agent.email_ai import analyze_email_with_claude

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(label, result, expected_type, expected_has_enough, expected_missing=None):
    if result is None:
        results.append((FAIL, label, "Claude returned None"))
        return

    actual_type = result.get("email_type")
    actual_enough = result.get("has_enough_info")
    actual_missing = result.get("missing_fields", [])

    errors = []
    if actual_type != expected_type:
        errors.append(f"email_type: expected={expected_type}, got={actual_type}")
    if actual_enough != expected_has_enough:
        errors.append(f"has_enough_info: expected={expected_has_enough}, got={actual_enough}")
    if expected_missing is not None:
        for field in expected_missing:
            if field not in actual_missing:
                errors.append(f"missing_fields: '{field}' not found in {actual_missing}")

    if errors:
        results.append((FAIL, label, " | ".join(errors)))
    else:
        results.append((PASS, label, f"reply: {result['suggested_reply'][:80]}..."))


# ──────────────────────────────────────────────
# 1. 가격 문의 - 정보 충분
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="john@gmail.com",
    subject="Price inquiry",
    body="Hi, I need a ride from Parramatta to Sydney International Airport on 2025-08-10. Flight at 09:00. 2 passengers, 1 large bag, 1 small bag.",
    thread_history=[{}]
)
check("가격문의 - 정보 충분", result, "price_inquiry", True)

# ──────────────────────────────────────────────
# 2. 가격 문의 - suburb 누락
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="jane@gmail.com",
    subject="How much?",
    body="Hi, how much is it to the airport on March 5? Flight at 07:30. 1 passenger.",
    thread_history=[{}]
)
check("가격문의 - suburb 누락", result, "price_inquiry", False, ["suburb"])

# ──────────────────────────────────────────────
# 3. 가격 문의 - 날짜 누락
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="bob@gmail.com",
    subject="Airport transfer",
    body="I'm in Chatswood and need a ride to the international airport. Flight at 6am. 2 pax, no luggage.",
    thread_history=[{}]
)
check("가격문의 - 날짜 누락", result, "price_inquiry", False, ["travel date"])

# ──────────────────────────────────────────────
# 4. 예약 요청 - flight_number, contact 누락
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="alice@gmail.com",
    subject="Book a shuttle",
    body="I'd like to book a shuttle from Bondi to the international airport on 2025-09-01. Flight at 10:00. 2 passengers, 2 large bags.",
    thread_history=[{}]
)
check("예약요청 - flight/contact 누락", result, "booking_request", False, ["flight number", "contact number"])

# ──────────────────────────────────────────────
# 5. 예약 확인 - thread 있고 모든 정보 있음 (CASE A)
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="mike@gmail.com",
    subject="Re: Booking confirmation",
    body="Yes, please go ahead and confirm my booking!",
    thread_history=[
        {"from": "mike@gmail.com", "date": "Mon, 1 Jul 2025", "body": "I need a ride from Manly to Sydney Airport on 2025-07-15. Flight QF001 at 08:00. 2 pax, 1 large bag. My number is 0412 345 678."},
        {"from": "info@easygoshuttle.com.au", "date": "Mon, 1 Jul 2025", "body": "Thanks! The price is $95. Please confirm to proceed."},
        {"from": "mike@gmail.com", "date": "Mon, 1 Jul 2025", "body": "Yes, please go ahead and confirm my booking!"},
    ]
)
check("예약확인 - CASE A (정보 완전)", result, "booking_confirmation", True)

# ──────────────────────────────────────────────
# 6. 예약 확인 - thread 없음 (CASE B)
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="sara@gmail.com",
    subject="Confirm booking",
    body="Please confirm my booking. Thanks.",
    thread_history=[{}]
)
check("예약확인 - CASE B (thread 없음)", result, "booking_confirmation", True)

# ──────────────────────────────────────────────
# 7. 예약 확인 - flight_number 누락 (CASE C)
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="tom@gmail.com",
    subject="Re: Booking",
    body="Yes confirmed, let's go ahead!",
    thread_history=[
        {"from": "tom@gmail.com", "date": "Tue, 2 Jul 2025", "body": "I need a ride from Newtown to the international airport on 2025-08-20 at 09:00. 1 passenger, no luggage. My number is 0400 111 222."},
        {"from": "info@easygoshuttle.com.au", "date": "Tue, 2 Jul 2025", "body": "Price is $75. Please confirm."},
        {"from": "tom@gmail.com", "date": "Tue, 2 Jul 2025", "body": "Yes confirmed, let's go ahead!"},
    ]
)
check("예약확인 - CASE C (flight_number 누락)", result, "booking_confirmation", False, ["flight number"])

# ──────────────────────────────────────────────
# 8. 클로징 메시지
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="lucy@gmail.com",
    subject="Re: Your booking",
    body="Thank you so much! See you then.",
    thread_history=[{}]
)
check("클로징 메시지", result, "closing_message", True, [])

# ──────────────────────────────────────────────
# 9. 일반 문의
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="guest@gmail.com",
    subject="Question",
    body="Do you provide child seats for toddlers?",
    thread_history=[{}]
)
check("일반문의", result, "general_inquiry", True)

# ──────────────────────────────────────────────
# 10. 결제 전화 요청
# ──────────────────────────────────────────────
result = analyze_email_with_claude(
    sender="dan@gmail.com",
    subject="Payment",
    body="Can I pay by credit card over the phone?",
    thread_history=[{}]
)
check("결제 전화 요청", result, "general_inquiry", True)

# ──────────────────────────────────────────────
# 결과 출력
# ──────────────────────────────────────────────
print("\n" + "="*60)
print("TEST RESULTS")
print("="*60)
for status, label, detail in results:
    print(f"{status}  [{label}]")
    print(f"       {detail}\n")

passed = sum(1 for s, _, _ in results if s == PASS)
total = len(results)
print("="*60)
print(f"TOTAL: {passed}/{total} passed")
print("="*60)
