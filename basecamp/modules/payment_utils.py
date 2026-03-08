import stripe

from main import settings
from utils.email import send_text_email
from blog.models import StripePayment


stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY


def paypal_ipn_error_email(subject, exception, item_name, payer_email, gross_amount):
    error_message = (
        f"Exception: {exception}\n"
        f"Payer Name: {item_name}\n"
        f"Payer Email: {payer_email}\n"
        f"Gross Amount: {gross_amount}"
    )
    send_text_email(subject, error_message, [settings.RECIPIENT_EMAIL])


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


def stripe_payment_error_email(subject, message, name, email, amount):
    content = f"""
    Subject: {subject}

    Error: {message}
    Name: {name}
    Email: {email}
    Amount: {amount}
    """
    send_text_email(subject, content, [settings.RECIPIENT_EMAIL])
