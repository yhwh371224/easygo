import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

import stripe

from main import settings
from utils.email import send_text_email
from blog.models import StripePayment


stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY

logger = logging.getLogger('easygo')

_CENT = Decimal('0.01')
_ELEVEN = Decimal('11')


def paypal_ipn_error_email(subject, exception, item_name, payer_email, gross_amount):
    error_message = (
        f"Exception: {exception}\n"
        f"Payer Name: {item_name}\n"
        f"Payer Email: {payer_email}\n"
        f"Gross Amount: {gross_amount}"
    )
    send_text_email(subject, error_message, [settings.RECIPIENT_EMAIL])


class StripeFeeNotReadyError(Exception):
    """Charge exists but Stripe hasn't attached balance_transaction yet.

    Raised by _record_stripe_fee so the caller (record_stripe_fee_task in
    basecamp.tasks) can retry after a delay instead of silently giving up —
    at webhook time this condition is the *normal* case, not an error.
    """


def _record_stripe_fee(payment_intent_id):
    """Create an expense Transaction for the Stripe processing fee.

    Fetches the PaymentIntent with latest_charge.balance_transaction expanded
    to obtain the GST-inclusive fee (Stripe AU charges 10% GST on fees).
    gst_amount = fee ÷ 11.

    Silently skips (no exception) if:
      - payment_intent_id is not a real PI string (e.g. starts with 'cs_')
      - fee is zero or negative
      - a Transaction with the same description already exists (duplicate guard)

    Raises StripeFeeNotReadyError if the charge/balance_transaction isn't
    attached yet — this is expected immediately after checkout.session.completed
    and the caller should retry shortly; it must NOT be treated as a real error.

    Other errors (bad API call, DB write failure) are logged and emailed; they
    never propagate to the caller.
    """
    from accounting.models import Transaction

    if not payment_intent_id or not str(payment_intent_id).startswith('pi_'):
        return

    description = f"Stripe fee {payment_intent_id}"

    # Duplicate guard — idempotent on repeated webhook deliveries / retries
    if Transaction.objects.filter(
        category='payment_fee',
        description=description,
    ).exists():
        logger.info('_record_stripe_fee: skipped duplicate for %s', payment_intent_id)
        return

    try:
        pi = stripe.PaymentIntent.retrieve(
            payment_intent_id,
            expand=['latest_charge.balance_transaction'],
        )

        charge = pi.latest_charge
        if not charge:
            raise StripeFeeNotReadyError(f"no latest_charge yet for {payment_intent_id}")

        bt = charge.balance_transaction
        # bt is a BalanceTransaction object when expanded; a bare string when not
        if not bt or isinstance(bt, str):
            raise StripeFeeNotReadyError(f"balance_transaction not expanded yet for {payment_intent_id}")

        fee_cents = bt.fee
        if not fee_cents or fee_cents <= 0:
            logger.info('_record_stripe_fee: zero fee for %s', payment_intent_id)
            return

        fee = (Decimal(fee_cents) / 100).quantize(_CENT)
        gst = (fee / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP)
        tx_date = datetime.date.fromtimestamp(bt.created)

        Transaction.objects.create(
            date=tx_date,
            direction='expense',
            brand='shuttle',
            description=description,
            gross_amount=fee,
            gst_code='gst',
            gst_amount=gst,
            category='payment_fee',
            source='stripe',
            counterparty='Stripe',
        )
        logger.info(
            '_record_stripe_fee: recorded fee=%.2f gst=%.2f for %s',
            fee, gst, payment_intent_id,
        )

    except StripeFeeNotReadyError:
        raise
    except Exception as exc:
        logger.exception('_record_stripe_fee: error for %s', payment_intent_id)
        send_text_email(
            f'Stripe fee recording error [{payment_intent_id}]',
            f"Failed to record Stripe fee for {payment_intent_id}:\n{exc}",
            [settings.RECIPIENT_EMAIL],
        )


# PayPal Australia treats its merchant transaction fees as a GST-free financial
# supply — unlike Stripe AU, PayPal does NOT add GST to seller fees, so there is
# no input-tax credit (1B) to claim. Fees are recorded as no_gst / zero GST.
# If a PayPal tax invoice ever shows a GST line, flip this to True.
_PAYPAL_FEE_HAS_GST = False


def _parse_paypal_date(payment_date):
    """Parse the PayPal IPN ``payment_date`` (e.g. '20:12:59 Jan 13, 2024 PST').

    The trailing timezone abbreviation is dropped (Python can't parse %Z for
    arbitrary abbreviations); falls back to today on any parse failure.
    """
    if payment_date:
        cleaned = payment_date.rsplit(' ', 1)[0]  # drop trailing tz abbrev
        for fmt in ('%H:%M:%S %b %d, %Y', '%H:%M:%S %b. %d, %Y'):
            try:
                return datetime.datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
    return datetime.date.today()


def _record_paypal_fee(txn_id, mc_fee, payment_date=None):
    """Create an expense Transaction for the PayPal processing fee (BAS 1B).

    ``mc_fee`` comes straight from the IPN payload — it is the exact fee PayPal
    deducted, so no API call is needed (contrast _record_stripe_fee). PayPal AU
    fees are GST-free, so gst_code='no_gst' and gst_amount=0 (see
    _PAYPAL_FEE_HAS_GST).

    Silently skips if:
      - txn_id is missing
      - mc_fee is missing / unparseable / not positive
      - a Transaction for this txn_id already exists (idempotent on duplicate IPNs)

    Errors are logged and emailed; they never propagate to the caller.
    """
    from accounting.models import Transaction

    if not txn_id:
        return

    description = f"PayPal fee {txn_id}"

    # Duplicate guard — idempotent on repeated IPN deliveries, keyed on txn_id
    if Transaction.objects.filter(
        category='payment_fee',
        description=description,
    ).exists():
        logger.info('_record_paypal_fee: skipped duplicate for %s', txn_id)
        return

    try:
        fee = Decimal(str(mc_fee)).quantize(_CENT)
    except (InvalidOperation, TypeError, ValueError):
        logger.warning('_record_paypal_fee: bad mc_fee %r for %s', mc_fee, txn_id)
        return

    if fee <= 0:
        logger.info('_record_paypal_fee: non-positive fee %s for %s', fee, txn_id)
        return

    if _PAYPAL_FEE_HAS_GST:
        gst_code = 'gst'
        gst = (fee / _ELEVEN).quantize(_CENT, rounding=ROUND_HALF_UP)
    else:
        gst_code = 'no_gst'
        gst = Decimal('0')

    try:
        Transaction.objects.create(
            date=_parse_paypal_date(payment_date),
            direction='expense',
            brand='shuttle',
            description=description,
            gross_amount=fee,
            gst_code=gst_code,
            gst_amount=gst,
            category='payment_fee',
            source='paypal',
            counterparty='PayPal',
        )
        logger.info(
            '_record_paypal_fee: recorded fee=%.2f gst=%.2f for %s',
            fee, gst, txn_id,
        )

    except Exception as exc:
        logger.exception('_record_paypal_fee: error for %s', txn_id)
        send_text_email(
            f'PayPal fee recording error [{txn_id}]',
            f"Failed to record PayPal fee for {txn_id}:\n{exc}",
            [settings.RECIPIENT_EMAIL],
        )


def handle_checkout_session_completed(session):
    email = session.customer_details.email
    name = session.customer_details.name
    amount = session.amount_total / 100
    payment_intent_id = session.payment_intent or session.id

    try:
        payment, created = StripePayment.objects.update_or_create(
            payment_intent_id=payment_intent_id,
            defaults={
                "name": name,
                "email": email,
                "amount": amount,
            }
        )
        print(f"StripePayment saved. created={created}")

    except Exception as e:
        stripe_payment_error_email(
            'Stripe Payment Save Error',
            str(e),
            name,
            email,
            amount
        )

    # Record Stripe processing fee as an expense Transaction for BAS 1B.
    # Delayed + retried via Celery: at webhook time Stripe hasn't attached
    # balance_transaction to the charge yet, so calling _record_stripe_fee
    # synchronously here missed 100% of fees (see incident 2026-07-11).
    if session.payment_intent:
        from basecamp.tasks import record_stripe_fee_task
        record_stripe_fee_task.apply_async(args=[session.payment_intent], countdown=20)


def stripe_payment_error_email(subject, message, name, email, amount):
    content = f"""
    Subject: {subject}

    Error: {message}
    Name: {name}
    Email: {email}
    Amount: {amount}
    """
    send_text_email(subject, content, [settings.RECIPIENT_EMAIL])
