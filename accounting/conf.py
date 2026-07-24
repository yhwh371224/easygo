from datetime import date
from decimal import Decimal

# GST registration confirmed with ATO effective 2026-07-01 (verified — not a placeholder).
GST_REGISTRATION_DATE = date(2026, 7, 1)

# Bank CSV import: director/owner wage net transfers — already in PayrollEntry.
# Substring match (via _contains_any). Skipped to prevent P&L double-count.
WAGE_SKIP_MARKERS = ['DIRECTOR WAGE']

# Bank CSV import: director capital contributions / repayments — already in
# DirectorLoan. Substring match (via _contains_any). These are balance-sheet
# items, not P&L — must never be imported as income or expense.
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
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN', 'OTR',
      'UNITED PETROLEUM', 'METRO PETROLEUM', 'FUEL', 'PETROL', 'VEZINA'), 'gst'),
    (('LINKT', 'E-TOLL', 'ETOLL', 'TOLL', 'TRANSURBAN'), 'gst'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH', 'CIRCUM VENDING'), 'gst'),
    (('TELSTRA', 'OPTUS', 'VODAFONE', 'TPG', 'AUSSIE BROADBAND',
      'BELONG', 'INTERNET', 'MOBILE'), 'gst'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'gst'),
    (('GROUP TRANSPORT',), 'gst'),
    (('NORTH SYDNEY EXECUTIVE', 'VIRTUAL OFFICE'), 'gst'),
    (('COUNCIL',), 'gst'),
    # Fines/infringements are never GST-eligible — explicit no_gst so this can
    # never be shadowed by a broader keyword added above in future.
    (('SDRO', 'INFRNGMNT', 'PENALTY'), 'no_gst'),
]

# These keywords force needs_review=True with no auto-GST, regardless of amount.
# insurance: stamp duty portion has no GST → manual split required to avoid 1B over-claim.
# vehicle_registration: CTP (REGO) is partly GST-free; SERVICE NSW fees vary.
REVIEW_OVERRIDE_KEYWORDS = (
    'INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH',
    'REGO', 'REGISTRATION', 'SERVICE NSW', 'TRANSPORT FOR NSW', 'RMS',
)

# Category auto-labelling (first match wins, falls back to 'uncategorised')
#
# Ordering note: vehicle_registration ('SERVICE NSW', ...) is checked BEFORE
# vehicle_maintenance ('SERVICE', ...) — 'SERVICE' is a substring of
# 'SERVICE NSW', so the broader vehicle_maintenance keyword would otherwise
# shadow the more specific registration match.
CATEGORY_KEYWORD_RULES = [
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN', 'OTR', 'FUEL',
      'PETROL', 'UNITED PETROLEUM', 'METRO PETROLEUM', 'VEZINA'), 'fuel'),
    (('LINKT', 'E-TOLL', 'ETOLL', 'TOLL', 'TRANSURBAN'), 'tolls'),
    (('REGO', 'REGISTRATION', 'SERVICE NSW', 'TRANSPORT FOR NSW', 'RMS'),
     'vehicle_registration'),
    (('SDRO', 'INFRNGMNT', 'PENALTY'), 'non_deductible_fine'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH', 'CIRCUM VENDING'), 'vehicle_maintenance'),
    (('TELSTRA', 'OPTUS', 'VODAFONE', 'TPG', 'AUSSIE BROADBAND',
      'BELONG', 'INTERNET', 'MOBILE'), 'phone_internet'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'marketing'),
    (('INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH'), 'insurance'),
    (('GROUP TRANSPORT',), 'subcontractor_payout'),
    (('NORTH SYDNEY EXECUTIVE', 'VIRTUAL OFFICE'), 'office_expense'),
]

# Categories that are imported for record-keeping but must NEVER be counted as
# a tax-deductible business expense (fines/infringements are non-deductible
# under ATO rules). Transaction.is_tax_deductible is set False for these on
# import; P&L/BAS aggregation excludes them from deductible expense totals.
NON_TAX_DEDUCTIBLE_CATEGORIES = {'non_deductible_fine'}
