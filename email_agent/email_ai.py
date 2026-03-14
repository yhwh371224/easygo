import anthropic
import json
from django.conf import settings
from basecamp.area_full import get_more_suburbs


def analyze_email_with_claude(sender, subject, body, thread_history):
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    history_text = ""
    if len(thread_history) > 1:
        history_text = "\n\n[Previous conversation]\n"
        for msg in thread_history[:-1]:
            history_text += f"From: {msg['from']}\nDate: {msg['date']}\n{msg['body']}\n---\n"

    suburbs = get_more_suburbs()
    suburb_list = list(suburbs.keys())

    prompt = f"""You are handling emails for EasyGo Airport Shuttle service in Sydney, Australia.

{history_text}

[New Email]
From: {sender}
Subject: {subject}
Body:
{body}

[Available Suburbs]
{suburb_list}

Analyze this email carefully and respond in JSON format only. No explanation, no markdown, just raw JSON.

{{
    "email_type": "price_inquiry" or "general_inquiry" or "booking_request" or "booking_related" or "other",
    "extracted_info": {{
        "suburb": "exact suburb name from the list above, or null if not found or not mentioned",
        "direction": "Pickup from Intl Airport" or "Pickup from Domestic Airport" or "Drop off to Intl Airport" or "Drop off to Domestic Airport" or "Cruise transfers or Point to Point" or null,
        "date": "YYYY-MM-DD or null",
        "flight_time": "HH:MM or null",
        "pickup_time": "HH:MM or null",
        "passengers": number or null,
        "large_luggage": number or null,
        "medium_small_luggage": number or null,
        "flight_number": "flight number or null",
        "contact_number": "phone number or null",
        "bike": number or null,
        "ski": number or null,
        "snow_board": number or null,
        "golf_bag": number or null,
        "musical_instrument": number or null,
        "carton_box": number or null
    }},
    "has_enough_info": true or false,
    "missing_fields": [],
    "suggested_reply": "draft reply in English"
}}

Rules for email_type:
- price_inquiry: customer asking for price/quote
- booking_request: customer wants to confirm/proceed with booking
- booking_related: existing booking change/cancel/question
- general_inquiry: other questions
- other: everything else

Rules for direction:
- Customer going TO airport = Drop off to (Intl or Domestic) Airport
- Customer coming FROM airport = Pickup from (Intl or Domestic) Airport
- No airport mentioned = Cruise transfers or Point to Point
- If airport involved but international/domestic unclear: direction = null, add "international or domestic flight" to missing_fields
- For Cruise transfers or Point to Point: flight_time is not needed, only pickup_time

Rules for flight_time vs pickup_time:
- flight_time: actual flight arrival or departure time (e.g. "arriving at HH:MM", "flight at HH:MM")
- pickup_time: only when customer explicitly says "pickup at HH:MM" or "please pick me up at HH:MM"

Rules for suburb:
- Match customer's location to the closest suburb in the list above
- Handle typos and variations
- If no match found: suburb = null, add "suburb" to missing_fields

Rules for has_enough_info:
- price_inquiry requires: suburb, direction, date, passengers, large_luggage, medium_small_luggage,  and either flight_time or pickup_time
  (For Cruise transfers or Point to Point: pickup_time only. Luggage fields default to 0 if not mentioned)
- booking_request requires: suburb, direction, date, passengers, large_luggage, medium_small_luggage, flight_number, contact_number, and either flight_time or pickup_time
- Special items (bike, ski, snow_board, golf_bag, musical_instrument, carton_box): ask only if customer mentions them, otherwise assume 0
- If customer says no luggage: set all luggage fields to 0 and do not ask again

Rules for missing_fields labels:
"suburb", "travel date", "number of passengers", "number of large luggage", "number of medium/small luggage", "flight time or pickup time",
"international or domestic flight", "departing or arriving", "pickup time",
"flight number", "contact number"

Rules for booking_request:
- Always ask for flight_number and contact_number if not provided
- If customer has no contact number: tell them we communicate via email, so please check email regularly especially on the day of travel
- If has_enough_info is true: say we will hold the booking and send a confirmation email shortly

Rules for suggested_reply:
- Keep it simple and concise, 3-4 sentences max
- Professional and friendly tone
- If missing info: ask only for the missing fields
- For luggage: if customer says no luggage or doesn't have any, treat as 0 and do not ask again
- If has_enough_info is true for price_inquiry: write naturally including {{PICKUP_TIME}} and {{PRICE}} placeholders, and invite customer to proceed with booking
- If has_enough_info is true for booking_request: say we will hold the booking and send a confirmation email shortly
- Never repeat back details the customer already provided
- For general_inquiry: answer helpfully
- Always end with "Kind regards,"
- Do NOT include signature (it will be added automatically)
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text

    # markdown 코드블록 제거
    response_text = response_text.strip()
    if response_text.startswith('```'):
        response_text = response_text.split('```')[1]
        if response_text.startswith('json'):
            response_text = response_text[4:]
        response_text = response_text.strip().rstrip('```')

    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response: {response_text}")
        return None
