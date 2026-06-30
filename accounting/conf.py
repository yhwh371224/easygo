from datetime import date
from decimal import Decimal

GST_REGISTRATION_DATE = date(2026, 7, 1)

# Bank CSV import: director/owner wage net transfers — already in PayrollEntry.
# Exact full-string match only (no substring). Skipped to prevent P&L double-count.
WAGE_SKIP_MARKERS = ['DIRECTOR WAGE']

# Bank CSV import: director capital contributions / repayments — already in
# DirectorLoan. Exact full-string match only. These are balance-sheet items,
# not P&L — must never be imported as income or expense.
LOAN_SKIP_MARKERS = ['LOAN FROM DIRECTOR']

# Bank CSV import: super contributions — fill in clearing house description after
# first payrun (e.g. 'AUSTRALIANSUPER', 'SUPERCHOICE'). Already in PayrollEntry.
SUPER_SKIP_MARKERS = []  # TBD after first real payrun

# Bank CSV import: expense rows at/above this amount are held for human triage.
REVIEW_THRESHOLD = Decimal('1000')

# Bank CSV import: own-account internal transfers — skip outright.
INTERNAL_TRANSFER_MARKERS = ['xx8784', 'CommBank app']

# GST auto-estimation rules (first match wins).
# Applied only to expense rows dated on/after GST_REGISTRATION_DATE.
# insurance and vehicle_registration intentionally omitted — see REVIEW_OVERRIDE_KEYWORDS.
GST_KEYWORD_RULES = [
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN',
      'UNITED PETROLEUM', 'METRO PETROLEUM', 'FUEL', 'PETROL'), 'gst'),
    (('LINKT', 'E-TOLL', 'ETOLL', 'TOLL', 'TRANSURBAN'), 'gst'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH'), 'gst'),
    (('TELSTRA', 'OPTUS', 'VODAFONE', 'TPG', 'AUSSIE BROADBAND',
      'BELONG', 'INTERNET', 'MOBILE'), 'gst'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'gst'),
]

# These keywords force needs_review=True with no auto-GST, regardless of amount.
# insurance: stamp duty portion has no GST → manual split required to avoid 1B over-claim.
# vehicle_registration: CTP (REGO) is partly GST-free; SERVICE NSW fees vary.
REVIEW_OVERRIDE_KEYWORDS = (
    'INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH',
    'REGO', 'REGISTRATION', 'SERVICE NSW', 'TRANSPORT FOR NSW', 'RMS',
)

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
