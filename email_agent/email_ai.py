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
    "email_type": "price_inquiry" or "general_inquiry" or "booking_related" or "other",
    "extracted_info": {{
        "suburb": "exact suburb name from the list above, or null if not found or not mentioned",
        "direction": "Pickup from Intl Airport" or "Pickup from Domestic Airport" or "Drop off to Intl Airport" or "Drop off to Domestic Airport" or "Cruise transfers or Point to Point" or null,
        "date": "YYYY-MM-DD or null",
        "flight_time": "HH:MM or null",
        "pickup_time": "HH:MM or null",
        "passengers": number or null,
        "large_luggage": number or null,
        "medium_small_luggage": number or null
    }},
    "has_enough_info": true or false,
    "missing_fields": [],
    "suggested_reply": "draft reply in English"
}}

Rules for direction:
- Customer going TO airport = Drop off to (Intl or Domestic) Airport
- Customer coming FROM airport = Pickup from (Intl or Domestic) Airport
- No airport mentioned (hotel to hotel, home to hotel, cruise, point to point, etc.) = Cruise transfers or Point to Point
- If airport involved but international/domestic is unclear, set direction to null and add "international or domestic flight" to missing_fields
- If no airport mentioned, always use "Cruise transfers or Point to Point" regardless of distance or route
- For "Cruise transfers or Point to Point", flight_time is not needed, only pickup_time

Rules for suburb:
- Match customer's location to the closest suburb in the list above
- Handle typos and variations
- If no match found, set to null and add "suburb" to missing_fields

Rules for has_enough_info (price_inquiry only):
- Must have: suburb, direction, pickup_date, no_of_passengers
- Must have either flight_time OR pickup_time
- If Cruise transfers or Point to Point: must have pickup_time only
- large_luggage and medium_small_luggage: if not mentioned, assume 0

Rules for missing_fields:
- Use clear English labels: "suburb", "travel date", "number of passengers",
  "flight time or pickup time", "international or domestic flight",
  "departing or arriving", "pickup time"

Rules for suggested_reply:
- Keep it simple and concise, 3-4 sentences max
- Professional and friendly tone but not overly verbose
- If missing info: politely ask only for the missing fields 
- If has_enough_info is true: say you will check availability and get back shortly
- Never repeat back all the details the customer provided
- For general_inquiry: answer helpfully
- Do NOT include sign-off or signature (it will be added automatically)
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
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

    return json.loads(response_text.strip())