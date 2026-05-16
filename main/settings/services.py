from decouple import config


# PayPal
PAYPAL_MODE = 'live'
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET')
PAYPAL_RECEIVER_EMAIL = 'info@easygoshuttle.com.au'
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

# Facebook / Instagram
FACEBOOK_PAGE_ID = config('FACEBOOK_PAGE_ID', default='')
FACEBOOK_PAGE_TOKEN = config('FACEBOOK_PAGE_TOKEN', default='')
INSTAGRAM_ACCOUNT_ID = config('INSTAGRAM_ACCOUNT_ID', default='')

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

# Honeypot
HONEYPOT_FIELD_NAME = 'phone_verify'
HONEYPOT_VALUE = ''

# Google
GOOGLE_REVIEW_URL = config('GOOGLE_REVIEW_URL')
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')
