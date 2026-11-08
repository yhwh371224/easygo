from decouple import config


# PayPal
PAYPAL_MODE = 'live'
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET')
PAYPAL_RECEIVER_EMAIL = config('PAYPAL_RECEIVER_EMAIL')
# Every PayPal account whose IPNs /paypal_ipn/ should accept; IPNs addressed to
# any other receiver are discarded (PayPal verifies them all as VERIFIED).
# info@easygoshuttle.com.au is the owner's second PayPal account — it sent real
# payment/refund IPNs here (e.g. 2026-09-14), so it stays accepted.
PAYPAL_RECEIVER_EMAILS = [PAYPAL_RECEIVER_EMAIL] + [
    e.strip() for e in config(
        'PAYPAL_EXTRA_RECEIVER_EMAILS', default='info@easygoshuttle.com.au',
    ).split(',') if e.strip()
]
PAYPAL_IPN_URL = 'https://easygoshuttle.com.au/paypal_ipn/'

# Stripe
STRIPE_MODE = 'live'
STRIPE_LIVE_SECRET_KEY = config('STRIPE_LIVE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY')

# Cloudflare Turnstile
CLOUDFLARE_TURNSTILE_SITE_KEY = config('CLOUDFLARE_TURNSTILE_SITE_KEY')
CLOUDFLARE_TURNSTILE_SECRET_KEY = config('CLOUDFLARE_TURNSTILE_SECRET_KEY')

# Anthropic / AI
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY')
# AI reply drafts only (Gmail watch/classification keep running). Drafts use the current email only (no thread history).
EMAIL_AI_DRAFTS_ENABLED = config('EMAIL_AI_DRAFTS_ENABLED', default=False, cast=bool)
EMAIL_AI_DUAL_MODE = config('EMAIL_AI_DUAL_MODE', default=False, cast=bool)
EMAIL_AI_OPENAI_ONLY = config('EMAIL_AI_OPENAI_ONLY', default=False, cast=bool)
# If True, emails with no airport keywords still get a cheap one-shot AIRPORT/OTHER LLM gate
# before skipping (extra API cost; default off for strict keyword-only gating).
EMAIL_AI_CLASSIFIER_FALLBACK = config('EMAIL_AI_CLASSIFIER_FALLBACK', default=False, cast=bool)

# Telegram
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID')

# Unsplash
UNSPLASH_ACCESS_KEY = config('UNSPLASH_ACCESS_KEY')
UNSPLASH_SECRET_KEY = config('UNSPLASH_SECRET_KEY')

# OpenAI
OPENAI_API_KEY = config('OPENAI_API_KEY')

# Google My Business
GMB_OAUTH_CLIENT_FILE = config('GMB_OAUTH_CLIENT_FILE', default='')
GMB_TOKEN_FILE = config('GMB_TOKEN_FILE', default='')
GMB_ACCOUNT_NAME = config('GMB_ACCOUNT_NAME', default='')
GMB_LOCATION_NAME = config('GMB_LOCATION_NAME', default='')

# Twilio
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN')
TWILIO_MESSAGING_SERVICE_SID = config('TWILIO_MESSAGING_SERVICE_SID')
TWILIO_WHATSAPP_FROM = config('TWILIO_WHATSAPP_FROM')

# Bird
BIRD_API_KEY = config('BIRD_API_KEY')
BIRD_NUMBER = config('BIRD_NUMBER')
BIRD_WORKSPACE_ID = config('BIRD_WORKSPACE_ID')
BIRD_CHANNEL_ID = config('BIRD_CHANNEL_ID')
BIRD_VOICE_CHANNEL_ID = config('BIRD_VOICE_CHANNEL_ID')

# Every number sync_bird_channels may wire to this site (comma-separated
# E.164); BIRD_NUMBER is always included. The Bird workspace is shared with
# BlackGlide, so anything not listed here — BlackGlide's numbers — is left
# alone. A newly bought easygo number must be added here before syncing.
BIRD_OWN_NUMBERS = config(
    'BIRD_OWN_NUMBERS', default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)

# Bird signs each webhook over the URL it was registered with, so subscription
# creation and signature verification must build that URL the same way — both
# read this base. Getting it wrong rejects every webhook, so it is one setting,
# not two.
BIRD_WEBHOOK_BASE_URL = config(
    'BIRD_WEBHOOK_BASE_URL',
    default='https://easygoshuttle.com.au',
).rstrip('/')

# Empty disables verification (endpoints stay open). Set it before running
# `manage.py sync_bird_channels`, which stamps it onto every subscription.
BIRD_WEBHOOK_SIGNING_KEY = config('BIRD_WEBHOOK_SIGNING_KEY', default='')

# Enforcement is a separate switch on purpose. Subscriptions created before the
# key existed send no signature, so turning verification on at the same moment
# the key lands would 403 every call. Deploy with this off, run
# sync_bird_channels, confirm the logs show signatures validating, then turn it
# on. While off, a bad signature is still rejected — only a missing one passes.
BIRD_WEBHOOK_REQUIRE_SIGNATURE = config(
    'BIRD_WEBHOOK_REQUIRE_SIGNATURE', default=False, cast=bool,
)

# Honeypot
HONEYPOT_FIELD_NAME = 'phone_verify'
HONEYPOT_VALUE = ''

# Google
GOOGLE_REVIEW_URL = config('GOOGLE_REVIEW_URL')
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')
