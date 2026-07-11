import logging

from celery import shared_task


logger = logging.getLogger('easygo')


@shared_task(bind=True, max_retries=6)
def record_stripe_fee_task(self, payment_intent_id):
    """Record the Stripe processing fee for a completed Checkout Session.

    Scheduled ~20s after checkout.session.completed (see
    basecamp.modules.payment_utils.handle_checkout_session_completed).
    Stripe doesn't always have balance_transaction attached to the charge
    that quickly; _record_stripe_fee raises StripeFeeNotReadyError in that
    case and this task retries with backoff (up to 6 attempts, 10-120s apart,
    ~6.5 min total). If it's still not ready after that, alert by email
    instead of failing silently — this exact silent-failure mode is why
    Stripe fees went unrecorded for every payment before this task existed
    (see incident 2026-07-11).
    """
    from basecamp.modules.payment_utils import _record_stripe_fee, StripeFeeNotReadyError
    from main import settings
    from utils.email import send_text_email

    try:
        _record_stripe_fee(payment_intent_id)
    except StripeFeeNotReadyError as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                'record_stripe_fee_task: giving up on %s after %d retries',
                payment_intent_id, self.request.retries,
            )
            send_text_email(
                f'Stripe fee recording gave up [{payment_intent_id}]',
                f"balance_transaction never became available after "
                f"{self.request.retries} retries for {payment_intent_id}. "
                f"Check the Stripe dashboard and record it manually if needed.",
                [settings.RECIPIENT_EMAIL],
            )
            return
        countdown = min(10 * (2 ** self.request.retries), 120)
        raise self.retry(exc=exc, countdown=countdown)
