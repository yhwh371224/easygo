from datetime import date
from decimal import Decimal

GST_REGISTRATION_DATE = date(2026, 7, 1)

# Bank CSV import: driver/subcontractor payments to SKIP outright (never created
# as a Transaction — these are payouts already captured by DriverSettlement).
#
# PRIMARY key — Mansoor's PayID mobile number. The import strips every non-digit
# from the description and tests whether this number is a substring. Store the
# national significant number WITHOUT the leading 0 or +61 country code: as 9
# digits it is a substring of every common rendering —
#     +61-425455302  ->  61425455302   (contains 425455302)
#     0425 455 302   ->  0425455302    (contains 425455302)
# This survives PayID display-name changes (e.g. "Paid to M JADOON +61-425455302"
# where the name is JADOON, not Mansoor). Spaces/hyphens in the value below are
# ignored — it is digit-normalised on use.
MANSOOR_PAYID = '425455302'   # Mansoor mobile, no leading 0 / no +61

# SECONDARY name safety net (case-insensitive regex against the upper-cased
# description) — backstop for rows that show the name but not the number.
# 'DON' was removed (too many false hits: DONUT / GORDON / DONCASTER).
DRIVER_SKIP_NAME_PATTERNS = [r'MANSOOR']

# Bank CSV import: expense rows at/above this amount are NOT auto-finalised as a
# BAS 1B expense. They import with needs_review=True and are held out of the
# BAS/P&L totals until a human approves (real expense) or excludes (driver
# payment) them in the admin.
REVIEW_THRESHOLD = Decimal('1000')

INTERNAL_TRANSFER_MARKERS = ['xx8784', 'CommBank app']

# GST auto-estimation rules (first match wins).
# Applied only to expense rows dated on/after GST_REGISTRATION_DATE.
GST_KEYWORD_RULES = [
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN',
      'UNITED PETROLEUM', 'METRO PETROLEUM', 'FUEL', 'PETROL'), 'gst'),
    (('LINKT', 'E-TOLL', 'ETOLL', 'TOLL', 'TRANSURBAN'), 'gst'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH'), 'gst'),
    (('TELSTRA', 'OPTUS', 'VODAFONE', 'TPG', 'AUSSIE BROADBAND',
      'BELONG', 'INTERNET', 'MOBILE'), 'gst'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'gst'),
    (('INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH'), 'gst'),
]

# Category auto-labelling (first match wins, falls back to 'uncategorised')
CATEGORY_KEYWORD_RULES = [
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN', 'FUEL',
      'PETROL', 'UNITED PETROLEUM', 'METRO PETROLEUM'), 'fuel'),
    (('LINKT', 'E-TOLL', 'ETOLL', 'TOLL', 'TRANSURBAN'), 'tolls'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH'), 'vehicle_maintenance'),
    (('TELSTRA', 'OPTUS', 'VODAFONE', 'TPG', 'AUSSIE BROADBAND',
      'BELONG', 'INTERNET', 'MOBILE'), 'phone_internet'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'marketing'),
    (('INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH'), 'insurance'),
    (('REGO', 'REGISTRATION', 'SERVICE NSW', 'TRANSPORT FOR NSW', 'RMS'),
     'vehicle_registration'),
]
