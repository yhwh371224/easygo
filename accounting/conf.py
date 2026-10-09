from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# GST registration confirmed with ATO effective 2026-07-01 (verified — not a placeholder).
GST_REGISTRATION_DATE = date(2026, 7, 1)

# PayPal card surcharge added on top of the price at checkout (payonline page,
# invoice surcharge 'Yes'), and backed out again when a payment is applied to
# Post.paid and when the surcharge is reported as income. Each payment uses the
# rate in force when it was made, so a rate change never restates old payments.
# 3% -> 2.5% from 2026-10-10 (owner, 2026-10-09): PayPal's own fee averaged
# ~2.39% of the booking amount in FY27 Q1, and a card surcharge should not
# exceed the cost of acceptance. Append new rates, oldest first.
PAYPAL_SURCHARGE_RATES = [
    (None, Decimal('0.03')),
    (datetime(2026, 10, 10, tzinfo=ZoneInfo('Australia/Sydney')), Decimal('0.025')),
]


def paypal_surcharge_rate(at=None):
    """PayPal surcharge rate in force at `at` (aware datetime, default now)."""
    from django.utils import timezone
    at = at or timezone.now()
    rate = PAYPAL_SURCHARGE_RATES[0][1]
    for start, r in PAYPAL_SURCHARGE_RATES[1:]:
        if at >= start:
            rate = r
    return rate

# Bank CSV import: director/owner wage net transfers — already in PayrollEntry.
# Substring match (via _contains_any). Skipped to prevent P&L double-count.
WAGE_SKIP_MARKERS = ['DIRECTOR WAGE']

# Bank CSV import: director capital contributions / repayments — already in
# DirectorLoan. Substring match (via _contains_any). These are balance-sheet
# items, not P&L — must never be imported as income or expense.
# 'LOAN FROM DIRECTOR' = contributions (director -> company); 'LOAN REPAYMENT'
# = repayments (company -> director), e.g. the 2026-08/09 $2,000 x 3
# settlement transfers. Both directions land in the same skip list since
# either way the movement is already recorded in DirectorLoan by hand.
# 'WDL ATM' / 'WDL BRANCH' = cash withdrawals by the director (ATM or branch
# counter), always put back into the company account the same or next day.
# Both legs are recorded in DirectorLoan by hand (confirmed by the owner
# 2026-10-08); the redeposit is income-side and skipped on import anyway.
LOAN_SKIP_MARKERS = ['LOAN FROM DIRECTOR', 'LOAN REPAYMENT', 'WDL ATM', 'WDL BRANCH']

# Bank CSV import: super contributions — already counted via PayrollEntry.super_amount
# in P&L (see reports.py labour_total). Importing the bank transfer too would double-count.
# 'PAYCLEAR' = Payclear Services Pty Ltd, the super clearing house used for real payruns
# (confirmed 2026-07-26: $156 transfer = 2 x $78 super_amount from PayrollEntry).
# 'SUPERCHOICE' = SuperChoice Services Pty Ltd, another clearing house used for the
# same payruns (confirmed 2026-08-05: $78 transfers match PayrollEntry.super_amount).
SUPER_SKIP_MARKERS = ['PAYCLEAR', 'SUPERCHOICE']

# Bank CSV import: payments to the ATO (BAS — GST + PAYG withholding, PAYG
# instalments, income tax). None of it is a P&L expense: GST is already kept
# out of P&L (figures are ex-GST), PAYGW is already in PayrollEntry.gross_pay
# (labour_total), and income tax comes after profit. Importing the bank row
# would double-count, so it is skipped like super / wage transfers.
# CommBank writes a BPAY to the ATO as e.g. 'TAX OFFICE PAYMENTS NetBank BPAY
# 75556 ...' (75556 = the ATO's BPAY biller code). 'ATO' itself is matched as a
# whole word (ATO_PAYMENT_PATTERN) so names like 'PLATO' or 'CURATOR' don't hit.
ATO_PAYMENT_MARKERS = ['TAX OFFICE', 'BPAY 75556']
ATO_PAYMENT_PATTERN = r'\bATO\b'

# Bank CSV import: driver/subcontractor payouts — already recorded as the
# 'subcontract' expense by DriverSettlement -> sync_settlement_expense(), so the
# bank row is skipped to avoid a P&L double-count. For payees the automatic
# driver matching misses: the bank writes 'Transfer To A REZAI PayID Phone from
# Net' (initial + surname, no PayID digits), which neither the full
# driver_name regex nor payment_match_digits can catch.
# 'A REZAI' = subcontractor, confirmed by the owner 2026-09-23.
# 'D S KANG' = subcontractor, written as 'Transfer To D S Kang NetBank EasyGo
#   to D...' (confirmed by the owner 2026-09-30).
# 'UBER *BUSINESS' = Uber rides booked for customers, i.e. Uber used as a
#   subcontractor (confirmed by the owner 2026-10-08), e.g. 'UBER *BUSINESS
#   TRIP HELP. Sydney AU Card xx9565'. Recorded as driver 'Ugo' (RASIER
#   PACIFIC PTY LTD, GST-registered) with the fare in the booking's
#   driver_price, so the settlement writes the 'subcontract' expense. Must
#   stay here (checked before PERSONAL_EXPENSE_MARKERS, which still holds the
#   broader 'UBER' for UBER *EATS).
# 'ENEX SERVICES' = ENEX SERVICES PTY LTD, where driver Don (Smile Pickup) asks
#   to be paid, e.g. 'Transfer To ENEX SERVICES PTY LTD PayID Phone from NetBank
#   EasyGo to Don smile pickup'. Don's settlement already writes the
#   'subcontract' expense (the 2026-08-31 and 2026-09-25 bank rows were both
#   duplicates; confirmed by the owner 2026-10-09). Settle Don BEFORE paying
#   ENEX, or the payout lands in no expense row at all.
DRIVER_PAYOUT_MARKERS = ['A REZAI', 'D S KANG', 'UBER *BUSINESS', 'ENEX SERVICES']

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
#   UBER — rideshare trips taken privately (confirmed 2026-08-20), and
#     'UBER *EATS' food delivery (confirmed 2026-09-30). From 2026-10-08
#     'UBER *BUSINESS' trips are subcontracted customer rides and are
#     caught earlier by DRIVER_PAYOUT_MARKERS, so never reach here. Note the
#     matching 'International Transaction Fee' rows cannot be tied back to the
#     Uber charge they belong to, so those stay as ordinary bank_fees.
#   NOMADESIM — travel eSIM data, bought for personal trips (confirmed
#     2026-08-20). Not the company mobile plan — that is SpinTel, billed
#     through PayPal (DODO before it).
#   NON CBA ATM WITHDRAWAL FEE — the fee on the director's cash withdrawals
#     (see 'WDL ATM' in LOAN_SKIP_MARKERS), charged to the director loan
#     rather than the company (confirmed by the owner 2026-10-08).
PERSONAL_EXPENSE_MARKERS = [
    'MUJI', 'UBER', 'NOMADESIM',
    'NON CBA ATM WITHDRAWAL FEE',
]
PERSONAL_EXPENSE_CATEGORY = 'personal_drawings'

# GST auto-estimation rules (first match wins).
# Applied only to expense rows dated on/after GST_REGISTRATION_DATE.
# insurance and vehicle_registration intentionally omitted — see REVIEW_OVERRIDE_KEYWORDS.
GST_KEYWORD_RULES = [
    # 'REDDY EXPRESS' = the rebranded Coles Express service stations (Viva
    # Energy / Shell), written by the bank as e.g.
    # '1589-REDDY EXPRESS WEST WEST RYDE AU'. Fuel, GST-inclusive (confirmed
    # by the owner 2026-09-16). Needs its own keyword — the row carries no
    # 'FUEL'/'PETROL'/'SHELL' word for the generic markers to catch.
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN', 'OTR',
      'UNITED PETROLEUM', 'METRO PETROLEUM', 'FUEL', 'PETROL', 'VEZINA',
      'REDDY EXPRESS'), 'gst'),
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
    # 'BIRD AMSTERDAM' = Bird (bird.com), the virtual-number / call-forwarding
    # provider behind the customer-facing numbers. Billed in AUD, GST-inclusive
    # (confirmed by the owner 2026-09-30), e.g. 'Bird Amsterdam NL Card xx9565'.
    (('BIRD AMSTERDAM',), 'gst'),
    # ENEX SERVICES PTY LTD — a driver payout (Don's jobs are paid out to ENEX
    # by request), NOT a GST-bearing purchase. The settlement is the authority
    # here: DriverSettlement -> sync_settlement_expense() already writes the
    # 'subcontract' expense row and decides its GST from driver.gst_registered,
    # so the bank row is a duplicate and must be excluded in admin. Forced to
    # 'no_gst' so that a row which slips through can never claim GST on its own
    # — without this rule 'SERVICE' (a substring of 'ENEX SERVICES') matches the
    # vehicle_maintenance keyword and silently produces a GST credit.
    # Normally unreachable now that 'ENEX SERVICES' is in DRIVER_PAYOUT_MARKERS
    # (skipped at import); kept as a backstop.
    (('ENEX',), 'no_gst'),
    # 'ULTRA TUNE' = Ultra Tune Artarmon, car servicing/mechanic — confirmed
    # a business vehicle cost by the owner (2026-09-09), always GST-inclusive.
    # Bank rows for this merchant carry varying prefixes (e.g. 'ZLR*Ultra
    # Tune Artarmon Artarmon AU') that don't hit the generic 'AUTO'/'SERVICE'
    # keywords below, so it needs its own explicit match.
    # 'YONGHOAN JUNG' (Lidcombe) = mobile mechanic called out to the vehicle,
    # GST-inclusive (confirmed by the owner 2026-09-23). The bank row is just
    # his name, e.g. 'YONGHOAN JUNG LIDCOMBE NSW AU'.
    # 'AMAZON MARKETPLACE' = company vehicle parts, GST-inclusive (confirmed by
    # the owner 2026-09-30). WARNING: this is every Amazon purchase — anything
    # bought there that is not a car part must be re-categorised in admin.
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH', 'CIRCUM VENDING', 'RIZKALLA',
      'ULTRA TUNE', 'YONGHOAN JUNG', 'AMAZON MARKETPLACE'), 'gst'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'gst'),
    (('GROUP TRANSPORT',), 'gst'),
    # 'OFFICEWORKS' = office supplies for the business (confirmed by the
    # owner 2026-09-23), e.g. 'OFFICEWORKS 0202 ALEXANDRIA AU'. GST-inclusive.
    # 'BUNNINGS' = business supplies, also confirmed by the owner 2026-09-23,
    # e.g. 'BUNNINGS 594000 ARTARMON AU'. GST-inclusive.
    (('NORTH SYDNEY EXECUTIVE', 'VIRTUAL OFFICE', 'CWH',
      'JB HI FI', 'JB HI-FI', 'OFFICEWORKS', 'BUNNINGS'), 'gst'),
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
    # INTERNATIONAL TRANSACTION FEE — the CommBank 3.5% FX fee, treated as a
    # business bank fee (owner, 2026-10-08): the foreign charges behind it are
    # now mostly business (e.g. VULTR billed in USD). It was a blanket
    # personal call before (2026-08-20) when UBER was personal. The CSV gives
    # no link back to the charge a fee belongs to, so a fee on a personal
    # foreign charge (e.g. NOMADESIM) must be flipped to personal in admin.
    # Bank fees are input-taxed financial supplies — no GST to claim.
    (('INTERNATIONAL TRANSACTION FEE',), 'no_gst'),
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
    # 'REDDY EXPRESS' — see the matching GST rule above.
    (('BP', 'CALTEX', 'AMPOL', 'SHELL', '7-ELEVEN', '7 ELEVEN', 'OTR', 'FUEL',
      'PETROL', 'UNITED PETROLEUM', 'METRO PETROLEUM', 'VEZINA',
      'REDDY EXPRESS'), 'fuel'),
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
    # Bird virtual numbers — see the matching GST rule above.
    (('BIRD AMSTERDAM',), 'phone_internet'),
    # ENEX SERVICES PTY LTD — subcontractor, confirmed by the owner
    # (2026-08-31): Smile Pickup asks for these jobs to be paid out to ENEX
    # directly via PayID. Checked BEFORE vehicle_maintenance because 'SERVICE'
    # is a substring of 'SERVICES' and would otherwise read as car servicing.
    # Normally unreachable: DRIVER_PAYOUT_MARKERS skips these rows at import.
    (('ENEX',), 'subcontractor_payout'),
    (('SERVICE', 'MECHANIC', 'AUTO', 'TYRE', 'TYRES', 'REPCO',
      'SUPERCHEAP', 'PANEL', 'SMASH', 'CIRCUM VENDING', 'RIZKALLA',
      'ULTRA TUNE', 'YONGHOAN JUNG', 'AMAZON MARKETPLACE'),
     'vehicle_maintenance'),
    (('GOOGLE', 'META', 'FACEBOOK', 'MARKETING', 'ADVERTIS', 'SEO'), 'marketing'),
    (('INSURANCE', 'NRMA', 'AAMI', 'ALLIANZ', 'QBE', 'GIO', 'ZURICH'), 'insurance'),
    (('GROUP TRANSPORT',), 'subcontractor_payout'),
    # JB Hi-Fi / Officeworks / Bunnings: consumables/equipment bought for the business.
    (('NORTH SYDNEY EXECUTIVE', 'VIRTUAL OFFICE', 'CWH',
      'JB HI FI', 'JB HI-FI', 'OFFICEWORKS', 'BUNNINGS'), 'office_expense'),
    (('COUNCI',), 'parking'),
    # VULTR: all charges are server/hosting costs (VPS provider).
    (('VULTR',), 'hosting'),
    # AI/dev tooling subscriptions — kept separate from 'hosting' (infrastructure)
    # so the recurring software spend is visible on its own P&L line.
    (('ANTHROPIC',), 'software_subscription'),
    # CommBank FX fee — see the matching GST rule above.
    (('INTERNATIONAL TRANSACTION FEE',), 'bank_fees'),
    (('TAXIPAY',), 'taxi'),
]

# Categories that are imported for record-keeping but must NEVER be counted as
# a tax-deductible business expense (fines/infringements are non-deductible
# under ATO rules; personal_drawings is not a company expense at all).
# Transaction.is_tax_deductible is set False for these on import; P&L/BAS
# aggregation excludes them from deductible expense totals.
# staff_entertainment = meal entertainment for staff (e.g. a team dinner at a
# restaurant). Under the FBT minor-benefit exemption (< $300 a head, no FBT
# paid) it is neither deductible nor eligible for a GST credit, so these rows
# are kept with gst_code='no_gst' (owner, 2026-10-08). If FBT is ever paid on
# such a benefit, flip the row back to deductible with its GST in admin.
NON_TAX_DEDUCTIBLE_CATEGORIES = {
    'non_deductible_fine', 'staff_entertainment', PERSONAL_EXPENSE_CATEGORY,
}
