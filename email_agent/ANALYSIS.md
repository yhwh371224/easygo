# Email Agent — Code Review & Analysis

> Reviewed: 2026-03-17

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Summaries](#component-summaries)
3. [Critical Bugs](#critical-bugs)
4. [Prompt Issues](#prompt-issues)
5. [Minor Issues](#minor-issues)
6. [Recommended Fixes](#recommended-fixes)
7. [Priority Summary](#priority-summary)

---

## Architecture Overview

```
Gmail Webhook (views.py)
  → decode Pub/Sub message
  → Celery task: gmail_watch_topic() (tasks.py)
      → fetch email via Gmail API
      → filter: skip spam / own emails / already-processed
      → get thread history (last 3 messages)
      → analyze_email_with_claude() (email_ai.py)
          → build_user_prompt() (user_template.py)
          → STATIC_SYSTEM_PROMPT (system_prompt.py)
          → Claude Haiku API → JSON response
      → if price_inquiry AND has_enough_info:
          → calculate_pickup_time() (price_utils.py)
          → calculate_price()       (price_utils.py)
          → replace {PICKUP_TIME}/{PRICE} placeholders in reply
      → append EMAIL_SIGNATURE
      → create_gmail_draft()
      → mark_message_processed()
```

---

## Component Summaries

### `views.py`
Single webhook endpoint (`/email_agent/webhook/`). Receives a Google Pub/Sub POST, base64-decodes the `message.data` field, and dispatches a Celery task. Returns HTTP 200 immediately so Pub/Sub doesn't retry. No business logic here — thin and correct.

### `tasks.py`
The main orchestrator. Responsibilities:
- Authenticate with Gmail via service account (domain delegation)
- Retrieve changed messages from Gmail History API
- Filter out own sent emails, spam/automated senders, already-processed messages
- Call Claude and receive structured JSON
- For price inquiries with enough info: calculate price + pickup time, inject into reply
- Create Gmail draft with HTML body + email signature
- Mark message with a Gmail label to prevent reprocessing
- Track the last processed `historyId` in a local file to avoid re-fetching old events

Notable constants:
- `LAST_HISTORY_ID_FILE` — path to file persisting the last Gmail history ID
- `PROCESSED_LABEL_ID` — Gmail label ID used to mark processed messages
- `EMAIL_SIGNATURE` — HTML block appended to every reply

### `email_ai.py`
Thin wrapper around the Anthropic SDK. Builds the user prompt, calls Claude Haiku with prompt caching on the system prompt (`"cache_control": {"type": "ephemeral"}`), and parses the JSON response. Strips markdown code fences if Claude wraps the JSON in them.

### `prompts/system_prompt.py`
Defines `STATIC_SYSTEM_PROMPT` — a single large string containing:
- Role definition (EasyGo Airport Shuttle agent)
- Output format: raw JSON schema
- Classification rules for `email_type`
- Field extraction rules (direction, suburb, flight_time vs pickup_time, luggage)
- `has_enough_info` rules per email type
- `missing_fields` label list
- Reply tone and content rules per email type
- Special-case handling: payments, booking confirmation cases A/B/C, closing messages

### `prompts/user_template.py`
Builds the user-side prompt by combining:
1. `[Available Suburbs]` — list of all serviced suburbs (fetched from `basecamp.area_full`, cached 1 hour)
2. `[Previous conversation]` — thread history (if any prior messages exist)
3. `[New Email]` — the incoming email's sender, subject, and body

### `price_utils.py`
Two main functions:
- `calculate_pickup_time()` — derives pickup time from flight time using fixed offsets per direction (e.g. Intl arrival: flight_time + 1hr, Intl drop-off: flight_time − 4hrs). Returns as-is if pickup_time was explicitly provided.
- `calculate_price()` — looks up base suburb price, adds per-passenger rate (formula differs for drop-off vs pickup), adds surcharge for excess luggage, and calculates special item surcharges (bike, ski, snowboard, etc.).

### `management/commands/watch_gmail.py`
One-off management command (`python manage.py watch_gmail`) to register or renew the Gmail push notification subscription. Gmail Watch expires every 7 days — this must be run periodically (e.g. via cron).

### `test_email_ai.py`
Manual smoke-test script. Runs 10 test scenarios against the live Claude API and prints pass/fail for each. Covers: price inquiry (sufficient/missing info), booking request, booking confirmation (cases A/B/C), closing message, general inquiry, phone payment request.

---

## Critical Bugs

### Bug 1 — Placeholder mismatch: price/pickup time never inserted into reply

**Files:** `prompts/system_prompt.py` and `tasks.py:140-143`

The system prompt instructs Claude to use double-brace placeholders:
```
write naturally including {{PICKUP_TIME}} and {{PRICE}} placeholders
```

Because `STATIC_SYSTEM_PROMPT` is a plain Python string (not an f-string), `{{PICKUP_TIME}}` is **literal** — two curly braces. Claude sees this and outputs `{{PICKUP_TIME}}` in `suggested_reply`.

But `tasks.py` replaces single-brace versions:
```python
reply_body = reply_body.replace('{PICKUP_TIME}', str(pickup_time))
reply_body = reply_body.replace('{PRICE}', f'${price} AUD')
```

Single-brace `{PICKUP_TIME}` will **never match** double-brace `{{PICKUP_TIME}}`. Every price inquiry draft gets sent with the raw placeholder text instead of actual values.

**Fix — Option A:** Change `tasks.py` to match what Claude outputs:
```python
reply_body = reply_body.replace('{{PICKUP_TIME}}', str(pickup_time) or 'TBC')
reply_body = reply_body.replace('{{PRICE}}', f'${price} AUD')
```

**Fix — Option B:** Change the system prompt to use single braces (simpler, less confusing):
```
write naturally including {PICKUP_TIME} and {PRICE} placeholders
```
(No change needed in `tasks.py` — it already uses single braces.)

---

### Bug 2 — `special_surcharge` calculated but never returned

**File:** `price_utils.py:30-34`

```python
special_surcharge = (bike + ski) * 20
special_surcharge += (snow_board + golf_bag + musical_instrument + carton_box) * 10

return base_price + luggage_surcharge   # ← special_surcharge silently dropped
```

Customers with bikes, skis, snowboards, golf bags, musical instruments, or carton boxes are quoted the wrong (lower) price.

**Fix:**
```python
return base_price + luggage_surcharge + special_surcharge
```

---

### Bug 3 — `email_type` JSON schema missing `booking_confirmation` and `closing_message`

**File:** `prompts/system_prompt.py:22`

The JSON schema defines:
```json
"email_type": "price_inquiry" or "general_inquiry" or "booking_request" or "booking_related" or "other"
```

But `booking_confirmation` and `closing_message` are only mentioned later in the Rules section. Claude must infer these are valid values from context, which is unreliable. This is a likely cause of misclassification — Claude may fall back to `"other"` or `"general_inquiry"` for booking confirmations and thank-you messages.

**Fix:**
```json
"email_type": "price_inquiry" | "booking_request" | "booking_confirmation" | "booking_related" | "closing_message" | "general_inquiry" | "other"
```

---

### Bug 4 — Hardcoded `/home/horeb/` paths cause runtime errors

**File:** `tasks.py:14` and `tasks.py:93`

```python
LAST_HISTORY_ID_FILE = '/home/horeb/github/easygo/last_history_id.txt'
# ...
logo_path = '/home/horeb/github/easygo/staticfiles/basecamp/images/easygo-logo-final.webp'
```

The current machine's user is `sung` (`/home/sung/`). Both paths will raise `FileNotFoundError` at runtime. The history ID file failing means the task will never know what's already been processed. The logo path failing means every draft creation will crash.

**Fix:**
```python
import os
from django.conf import settings

LAST_HISTORY_ID_FILE = os.path.join(settings.BASE_DIR, 'last_history_id.txt')
# ...
logo_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'basecamp', 'images', 'easygo-logo-final.webp')
```

---

## Prompt Issues

### Issue 5 — No `has_enough_info` rule for `general_inquiry`, `booking_related`, or `other`

**File:** `prompts/system_prompt.py` — "Rules for has_enough_info" section

The rules explicitly cover `price_inquiry`, `booking_request`, `booking_confirmation`, and `closing_message` — but say nothing about `general_inquiry`, `booking_related`, or `other`. Claude has to guess, and may inconsistently return `false` or populate `missing_fields` for these types.

The test suite (test case 9) expects `has_enough_info = true` for a general inquiry, but this is never stated in the prompt.

**Fix — add explicit rules:**
```
- general_inquiry: always set has_enough_info to true. missing_fields = [].
- booking_related: always set has_enough_info to true. missing_fields = [].
- other: always set has_enough_info to true. missing_fields = [].
```

---

### Issue 6 — Suburb list renders as Python list repr, not clean text

**File:** `prompts/user_template.py:5-6`

`get_suburb_list()` returns a Python `list` object. When interpolated into the f-string, it renders as:
```
[Available Suburbs]
['Parramatta', 'Chatswood', 'Bondi Junction', ...]
```

The Python list format works, but it's noisy and wastes tokens. A comma-separated or newline-separated string is cleaner and easier for the model to parse.

**Fix in `user_template.py`:**
```python
def build_user_prompt(sender, subject, body, history_text, suburb_list):
    if isinstance(suburb_list, list):
        suburb_str = ', '.join(suburb_list)
    else:
        suburb_str = suburb_list

    return f"""[Available Suburbs]
{suburb_str}
...
```

---

### Issue 7 — Luggage default-to-zero rule only applies to Cruise transfers

**File:** `prompts/system_prompt.py` — "Rules for has_enough_info" section

```
price_inquiry requires: suburb, direction, date, passengers, large_luggage,
medium_small_luggage, and either flight_time or pickup_time
(For Cruise transfers or Point to Point: pickup_time only. Luggage fields default to 0 if not mentioned)
```

The parenthetical "Luggage fields default to 0 if not mentioned" is scoped only to Cruise transfers. For airport transfers, if a customer doesn't mention luggage, Claude will flag it as missing and ask — even though "no luggage" is a perfectly valid answer.

Most customers don't mention luggage explicitly if they have none. This causes unnecessary back-and-forth.

**Fix:** Move the luggage default rule to apply globally:
```
price_inquiry requires: suburb, direction, date, passengers, and either flight_time
or pickup_time. Luggage fields (large_luggage, medium_small_luggage) default to 0 if
not mentioned — do NOT ask for luggage info unless the customer brings it up.
```

---

### Issue 8 — Thread history messages not labelled by sender role

**File:** `email_ai.py:_build_history_text()`

```python
lines.append(f"From: {from_}\nDate: {date}\n{body}\n---")
```

Claude receives raw `From:` header values (e.g. `"Mike Smith <mike@gmail.com>"` vs `"EasyGo Shuttle <info@easygoshuttle.com.au>"`). When the conversation context matters (booking confirmation Case A/C), Claude must figure out which messages are from the customer and which are from EasyGo. This works most of the time, but can fail with display names or forwarded emails.

**Improvement:** Normalize labels:
```python
role = 'EasyGo' if 'info@easygoshuttle.com.au' in msg['from'] else 'Customer'
lines.append(f"[{role}] {msg['date']}\n{msg['body']}\n---")
```

---

### Issue 9 — `suggested_reply` for `price_inquiry` with enough info doesn't instruct Claude to include the date and direction summary

**File:** `prompts/system_prompt.py` — "Rules for suggested_reply"

The instruction is:
```
If has_enough_info is true for price_inquiry: write naturally including
{PICKUP_TIME} and {PRICE} placeholders, and invite customer to proceed with booking
```

There's no instruction about what other context to include. A good price-inquiry reply should confirm the key details (date, direction, pickup time, price) so the customer can verify before booking. Without guidance, Claude may produce a vague reply like "Your price is {PRICE} and pickup is at {PICKUP_TIME}. Please let us know if you'd like to proceed."

**Improvement:**
```
If has_enough_info is true for price_inquiry: write a warm, clear reply that
confirms the travel date, direction, pickup time ({PICKUP_TIME}), and total price
({PRICE}). Then invite the customer to reply to proceed with booking. Keep it
concise — 3-4 sentences.
```

---

## Minor Issues

### Issue 10 — `get_thread_history` only fetches last 3 messages; older context is silently lost

**File:** `tasks.py` — `get_thread_history(service, thread_id, max_messages=3)`

If a conversation has more than 3 messages (e.g. a long back-and-forth about a booking), the older messages are dropped. For booking confirmation Case A, Claude needs to find the flight number and contact number from the thread — if those were in message 4 or earlier, they're not available, and Claude will incorrectly classify as Case C and ask again.

**Improvement:** Increase `max_messages` to 5 or 6, or make it configurable via settings.

---

### Issue 11 — `test_email_ai.py` makes live API calls with no mocking

**File:** `test_email_ai.py`

The test file directly calls `analyze_email_with_claude()`, making real Anthropic API calls on every test run. This costs money, is slow, and is non-deterministic. It also can't run in CI without a real API key.

**Improvement:** Mock the Anthropic client in unit tests. Keep the live-call version as an integration test only, clearly labelled.

---

### Issue 12 — Gmail Watch command has no scheduling mechanism

**File:** `management/commands/watch_gmail.py`

Gmail Watch subscriptions expire every 7 days. The management command must be re-run manually or via cron. There's no reminder, no auto-renewal, and no check for when the current watch expires. If it lapses, emails stop being processed silently.

**Improvement:** Add a Celery beat task that runs `watch_gmail` every 6 days, or at minimum log the expiration timestamp so it can be monitored.

---

## Recommended Fixes

### Fix 1 — `tasks.py`: resolve hardcoded paths (lines 14, 93)

```python
# Before
LAST_HISTORY_ID_FILE = '/home/horeb/github/easygo/last_history_id.txt'
logo_path = '/home/horeb/github/easygo/staticfiles/basecamp/images/easygo-logo-final.webp'

# After
import os
from django.conf import settings

LAST_HISTORY_ID_FILE = os.path.join(settings.BASE_DIR, 'last_history_id.txt')
logo_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'basecamp', 'images', 'easygo-logo-final.webp')
```

### Fix 2 — `tasks.py`: fix placeholder replacement (lines 140-143)

```python
# Before
reply_body = reply_body.replace('{PICKUP_TIME}', str(pickup_time))
reply_body = reply_body.replace('{PRICE}', f'${price} AUD')

# After (matching the double-brace format Claude outputs)
reply_body = reply_body.replace('{{PICKUP_TIME}}', str(pickup_time) or 'TBC')
reply_body = reply_body.replace('{{PRICE}}', f'${price} AUD')
```

### Fix 3 — `price_utils.py`: add `special_surcharge` to return value (line 34)

```python
# Before
return base_price + luggage_surcharge

# After
return base_price + luggage_surcharge + special_surcharge
```

### Fix 4 — `system_prompt.py`: add missing `email_type` values to JSON schema

```python
# Before
"email_type": "price_inquiry" or "general_inquiry" or "booking_request" or "booking_related" or "other",

# After
"email_type": "price_inquiry" | "booking_request" | "booking_confirmation" | "booking_related" | "closing_message" | "general_inquiry" | "other",
```

### Fix 5 — `system_prompt.py`: add `has_enough_info` rules for remaining email types

Add after the `closing_message` rule in the "Rules for has_enough_info" section:

```
- general_inquiry: always set has_enough_info to true. missing_fields = [].
- booking_related: always set has_enough_info to true. missing_fields = [].
- other: always set has_enough_info to true. missing_fields = [].
```

### Fix 6 — `system_prompt.py`: make luggage default-to-zero apply globally

```
# Before (scoped to Cruise only)
(For Cruise transfers or Point to Point: pickup_time only. Luggage fields default to 0 if not mentioned)

# After (applies to all types)
Luggage fields (large_luggage, medium_small_luggage) default to 0 if not mentioned.
Do NOT ask for luggage info unless the customer mentions it.
For Cruise transfers or Point to Point: only pickup_time is needed, not flight_time.
```

### Fix 7 — `user_template.py`: format suburb list as readable text

```python
def build_user_prompt(sender, subject, body, history_text, suburb_list):
    if isinstance(suburb_list, list):
        suburb_str = ', '.join(suburb_list)
    else:
        suburb_str = suburb_list

    return f"""[Available Suburbs]
{suburb_str}

{history_text}

[New Email]
From: {sender}
Subject: {subject}
Body:
{body}"""
```

### Fix 8 — `email_ai.py`: label thread messages by role

```python
def _build_history_text(thread_history):
    if len(thread_history) <= 1:
        return ""
    lines = ["\n\n[Previous conversation]"]
    for msg in thread_history[:-1]:
        role = 'EasyGo' if 'info@easygoshuttle.com.au' in msg.get('from', '') else 'Customer'
        lines.append(f"[{role}] {msg['date']}\n{msg['body']}\n---")
    return "\n".join(lines)
```

---

## Priority Summary

| Priority | File | Location | Issue |
|---|---|---|---|
| 🔴 Critical | `tasks.py` | lines 140–143 | Placeholder mismatch — price/pickup time never inserted into reply |
| 🔴 Critical | `price_utils.py` | line 34 | `special_surcharge` calculated but not included in return value |
| 🔴 Critical | `system_prompt.py` | line 22 | `booking_confirmation` and `closing_message` missing from JSON schema |
| 🔴 Critical | `tasks.py` | lines 14, 93 | Hardcoded `/home/horeb/` paths — runtime `FileNotFoundError` |
| 🟡 Medium | `system_prompt.py` | has_enough_info rules | No rules defined for `general_inquiry`, `booking_related`, `other` |
| 🟡 Medium | `system_prompt.py` | has_enough_info rules | Luggage default-to-zero only scoped to Cruise transfers |
| 🟡 Medium | `system_prompt.py` | suggested_reply rules | Price inquiry reply lacks instruction to confirm booking details |
| 🟡 Medium | `user_template.py` | `build_user_prompt()` | Suburb list renders as Python list repr — noisy and token-wasteful |
| 🟡 Medium | `email_ai.py` | `_build_history_text()` | Thread messages not labelled by role (Customer vs EasyGo) |
| 🟢 Low | `tasks.py` | `get_thread_history()` | Only last 3 messages fetched — older booking context silently lost |
| 🟢 Low | `test_email_ai.py` | entire file | Live API calls in tests — no mocking, costs money, non-deterministic |
| 🟢 Low | `management/commands/` | `watch_gmail.py` | No auto-renewal for Gmail Watch (expires every 7 days) |
