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

# Bank CSV import: super contributions — already counted via PayrollEntry.super_amount
# in P&L (see reports.py labour_total). Importing the bank transfer too would double-count.
# 'PAYCLEAR' = Payclear Services Pty Ltd, the super clearing house used for real payruns
# (confirmed 2026-07-26: $156 transfer = 2 x $78 super_amount from PayrollEntry).
# 'SUPERCHOICE' = SuperChoice Services Pty Ltd, another clearing house used for the
# same payruns (confirmed 2026-08-05: $78 transfers match PayrollEntry.super_amount).
SUPER_SKIP_MARKERS = ['PAYCLEAR', 'SUPERCHOICE']

# Bank CSV import: expense rows at/above this amount are held for human triage.
REVIEW_THRESHOLD = Decimal('1000')

# Bank CSV import: own-account internal transfers — skip outright.
INTERNAL_TRANSFER_MARKERS = ['xx8784', 'CommBank app']

# Bank CSV import: personal (non-business) spending that went through the
# company account. These are NOT skipped — they are imported with
# excluded=True so the owner can see what is owed back to the company — but
# they never reach P&L or BAS (no GST claim, no deduction).
# Confirmed personal by the owner:
#   MUJI — homeware/stationery retail, personal purchases only.
#   UBER — rideshare trips taken privately (confirmed 2026-08-20). Note the
#     matching 'International Transaction Fee' rows cannot be tied back to the
#     Uber charge they belong to, so those stay as ordinary bank_fees.
#   NOMADESIM — travel eSIM data, bought for personal trips (confirmed
#     2026-08-20). Not the company mobile plan — that is SpinTel, billed
#     through PayPal (DODO before it).
#   INTERNATIONAL TRANSACTION FEE — the CommBank 3.5% FX fee. Every such fee
#     seen so far belongs to a personal foreign charge (UBER, NOMADESIM);
#     Anthropic, the one foreign business charge, is billed in AUD and raises
#     no fee. The CSV gives no link back to the charge a fee belongs to, so
#     this is a blanket call by the owner (2026-08-20). If a foreign *business*
#     charge is ever billed in USD (e.g. VULTR), its fee will be caught here
#     too and must be flipped back to a business expense in admin.
PERSONAL_EXPENSE_MARKERS = [
    'MUJI', 'UBER', 'NOMADESIM', 'INTERNATIONAL TRANSACTION FEE',
]
PERSONAL_EXPENSE_CATEGORY = 'personal_drawings'

# GST auto-estimation rules (first match wins).
# Applied only to expense rows dated on/after GST_REGISTRATION_DATE.
# insurance and vehicle_registration intentionally omitted — see REVIEW_OVERRIDE_KEYWORDS.
GST_KEYWORD_RULES = [
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN', 'OTR',
      'UNITED PETROLEUM', 'METRO PETROLEUM', 'FUEL', 'PETROL', 'VEZINA'), 'gst'),
    (('LINKT', 'E-TOLL', 'ETOLL', 'TOLL', 'TRANSURBAN'), 'gst'),
    # 'RIZKALLA' = J RIZKALLA & J VISVI (North Sydney) — car servicing, confirmed
    # a business vehicle cost by the owner. Merchant name, not a generic word.
    # 'DODO' and the phone/internet carriers must stay ahead of the
    # vehicle_maintenance 'SERVICE' keyword — the bank writes some of these
    # as e.g. 'DODO SERVICES PTY LTD' / 'TELSTRA SERVICES MELBOURNE AU',
    # and 'SERVICE' is a substring of both. They are the phone/internet
    # bill, not car servicing.
    (('DODO',), 'gst'),
    # SPINTEL = the current mobile + internet plan. The bill is paid through
    # PayPal, so the bank row carries no merchant name at all — only PayPal's
    # direct-debit reference, e.g. 'Direct Debit 617704 PAYPAL AUSTRALIA
    # 105...'. 617704 is PayPal Australia's *debit* APCA user ID; 617702 is the
    # credit side (incoming PayPal payouts), which is income and skipped on
    # import, so this rule can never touch it. Charged GST-inclusive
    # (confirmed by the owner 2026-08-28).
    # WARNING: any *other* purchase funded from the bank via PayPal would carry
    # the same 617704 reference and be treated as a phone bill here. The
    # SpinTel plan is a fixed monthly amount ($159.95 as at 2026-08) — if a
    # PayPal debit for a different amount shows up, re-categorise it in admin.
    (('SPINTEL', '617704 PAYPAL'), 'gst'),
    (('TELSTRA', 'OPTUS', 'VODAFONE', 'TPG', 'AUSSIE BROADBAND',
      'BELONG', 'INTERNET', 'MOBILE'), 'gst'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH', 'CIRCUM VENDING', 'RIZKALLA'), 'gst'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'gst'),
    (('GROUP TRANSPORT',), 'gst'),
    (('NORTH SYDNEY EXECUTIVE', 'VIRTUAL OFFICE', 'CWH',
      'JB HI FI', 'JB HI-FI'), 'gst'),
    # 'COUNCI' (not 'COUNCIL') — CommBank truncates some council names, e.g.
    # 'WILLOUGHBY CITY COUNCI'. Substring match still covers the full spelling.
    (('COUNCI',), 'gst'),
    (('VULTR',), 'gst'),
    # ANTHROPIC (Claude subscription) — used for company systems work and
    # project coding, so a business expense. Billed in AUD with 10% AU GST
    # included; if an ABN is ever registered with Anthropic the charge becomes
    # GST-free (B2B reverse charge) and this rule must move to 'gst_free'.
    (('ANTHROPIC',), 'gst'),
    # 'TFNSW' = Transport for NSW, billed as '200 TFNSW INTER/IVR ...'.
    # These are driver test / licence fees, charged GST-inclusive (confirmed
    # by the owner 2026-08-20). Kept separate from the broader
    # 'TRANSPORT FOR NSW' spelling, which stays in REVIEW_OVERRIDE_KEYWORDS
    # because it also covers rego-type charges with mixed GST treatment.
    (('TFNSW',), 'gst'),
    # Currently unreachable: the same string is in PERSONAL_EXPENSE_MARKERS,
    # which is matched first and skips GST entirely. Kept so the fee falls back
    # to a correct business treatment if that personal marker is ever removed.
    (('INTERNATIONAL TRANSACTION FEE',), 'gst'),
    (('TAXIPAY',), 'gst'),
    # Fines/infringements are never GST-eligible — explicit no_gst so this can
    # never be shadowed by a broader keyword added above in future.
    (('SDRO', 'INFRNGMNT', 'PENALTY'), 'no_gst'),
]

# These keywords force needs_review=True with no auto-GST, regardless of amount.
# insurance: stamp duty portion has no GST → manual split required to avoid 1B over-claim.
# vehicle_registration: CTP (REGO) is partly GST-free; SERVICE NSW fees vary.
# refund: customer refunds are usually already recorded on the booking (Post.refund,
# netted off 1A) — always held for review so the owner can confirm that and mark the
# bank row excluded, instead of it silently landing in P&L as an ordinary expense.
REVIEW_OVERRIDE_KEYWORDS = (
    'INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH',
    'REGO', 'REGISTRATION', 'SERVICE NSW', 'TRANSPORT FOR NSW', 'RMS',
    'REFUND',
)

# Category auto-labelling (first match wins, falls back to 'uncategorised')
#
# Ordering note: vehicle_registration ('SERVICE NSW', ...) is checked BEFORE
# vehicle_maintenance ('SERVICE', ...) — 'SERVICE' is a substring of
# 'SERVICE NSW', so the broader vehicle_maintenance keyword would otherwise
# shadow the more specific registration match. Same reason phone_internet
# ('DODO', 'TELSTRA', ...) and the ENEX subcontractor rule sit above
# vehicle_maintenance: the bank writes e.g. 'DODO SERVICES PTY LTD',
# 'TELSTRA SERVICES MELBOURNE AU' and 'ENEX SERVICES PTY LTD', all of which
# contain 'SERVICE'.
CATEGORY_KEYWORD_RULES = [
    (('REFUND',), 'customer_refund'),
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN', 'OTR', 'FUEL',
      'PETROL', 'UNITED PETROLEUM', 'METRO PETROLEUM', 'VEZINA'), 'fuel'),
    (('LINKT', 'E-TOLL', 'ETOLL', 'TOLL', 'TRANSURBAN'), 'tolls'),
    # 'TFNSW' ('200 TFNSW INTER/IVR SURRY HILLS') = Transport for NSW driver
    # test / licence fees. Checked before vehicle_registration so it lands on
    # its own line rather than being read as a rego cost.
    (('TFNSW',), 'licence_fees'),
    (('REGO', 'REGISTRATION', 'SERVICE NSW', 'TRANSPORT FOR NSW', 'RMS'),
     'vehicle_registration'),
    (('SDRO', 'INFRNGMNT', 'PENALTY'), 'non_deductible_fine'),
    # DODO Services Pty Ltd / TELSTRA SERVICES / etc. = phone or internet
    # bills. Checked BEFORE vehicle_maintenance because 'SERVICE' is a
    # substring of both and would otherwise label them as car servicing.
    (('DODO',), 'phone_internet'),
    # SpinTel, direct-debited by PayPal — see the matching GST rule above for
    # why the bank reference ('617704 PAYPAL') is the only usable marker.
    (('SPINTEL', '617704 PAYPAL'), 'phone_internet'),
    (('TELSTRA', 'OPTUS', 'VODAFONE', 'TPG', 'AUSSIE BROADBAND',
      'BELONG', 'INTERNET', 'MOBILE'), 'phone_internet'),
    # ENEX SERVICES PTY LTD — subcontractor, confirmed by the owner
    # (2026-08-31): Smile Pickup asks for these jobs to be paid out to ENEX
    # directly via PayID. Checked BEFORE vehicle_maintenance because 'SERVICE'
    # is a substring of 'SERVICES' and would otherwise read as car servicing.
    (('ENEX',), 'subcontractor_payout'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH', 'CIRCUM VENDING', 'RIZKALLA'),
     'vehicle_maintenance'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'marketing'),
    (('INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH'), 'insurance'),
    (('GROUP TRANSPORT',), 'subcontractor_payout'),
    # JB Hi-Fi: office consumables/equipment bought for the office.
    (('NORTH SYDNEY EXECUTIVE', 'VIRTUAL OFFICE', 'CWH',
      'JB HI FI', 'JB HI-FI'), 'office_expense'),
    (('COUNCI',), 'parking'),
    # VULTR: all charges are server/hosting costs (VPS provider).
    (('VULTR',), 'hosting'),
    # AI/dev tooling subscriptions — kept separate from 'hosting' (infrastructure)
    # so the recurring software spend is visible on its own P&L line.
    (('ANTHROPIC',), 'software_subscription'),
    # Also shadowed by PERSONAL_EXPENSE_MARKERS — see the GST rule above.
    (('INTERNATIONAL TRANSACTION FEE',), 'bank_fees'),
    (('TAXIPAY',), 'taxi'),
]

# Categories that are imported for record-keeping but must NEVER be counted as
# a tax-deductible business expense (fines/infringements are non-deductible
# under ATO rules; personal_drawings is not a company expense at all).
# Transaction.is_tax_deductible is set False for these on import; P&L/BAS
# aggregation excludes them from deductible expense totals.
NON_TAX_DEDUCTIBLE_CATEGORIES = {'non_deductible_fine', PERSONAL_EXPENSE_CATEGORY}
