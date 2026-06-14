import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP

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


def _record_stripe_fee(payment_intent_id):
    """Create an expense Transaction for the Stripe processing fee.

    Fetches the PaymentIntent with latest_charge.balance_transaction expanded
    to obtain the GST-inclusive fee (Stripe AU charges 10% GST on fees).
    gst_amount = fee ÷ 11.

    Silently skips if:
      - payment_intent_id is not a real PI string (e.g. starts with 'cs_')
      - balance_transaction is not yet available
      - fee is zero or negative
      - a Transaction with the same description already exists (duplicate guard)

    Errors are logged and emailed; they never propagate to the caller.
    """
    from accounting.models import Transaction

    if not payment_intent_id or not str(payment_intent_id).startswith('pi_'):
        return

    description = f"Stripe fee {payment_intent_id}"

    # Duplicate guard — idempotent on repeated webhook deliveries
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
            logger.warning('_record_stripe_fee: no latest_charge for %s', payment_intent_id)
            return

        bt = charge.balance_transaction
        # bt is a BalanceTransaction object when expanded; a bare string when not
        if not bt or isinstance(bt, str):
            logger.warning('_record_stripe_fee: balance_transaction not expanded for %s', payment_intent_id)
            return

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

    except Exception as exc:
        logger.exception('_record_stripe_fee: error for %s', payment_intent_id)
        send_text_email(
            f'Stripe fee recording error [{payment_intent_id}]',
            f"Failed to record Stripe fee for {payment_intent_id}:\n{exc}",
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
    # Runs after StripePayment save; errors are caught internally.
    _record_stripe_fee(session.payment_intent)


def stripe_payment_error_email(subject, message, name, email, amount):
    content = f"""
    Subject: {subject}

    Error: {message}
    Name: {name}
    Email: {email}
    Amount: {amount}
    """
    send_text_email(subject, content, [settings.RECIPIENT_EMAIL])
