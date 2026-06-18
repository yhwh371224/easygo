from datetime import date

GST_REGISTRATION_DATE = date(2026, 7, 1)

# Bank CSV import: rows to SKIP
DRIVER_SKIP_NAMES = ['MANSOOR', 'DON']
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
