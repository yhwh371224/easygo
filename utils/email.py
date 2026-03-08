import logging
import uuid

from django.conf import settings
from django.core.mail import send_mail as _django_send_mail, EmailMultiAlternatives
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_text_email(subject, message, recipient_list, from_email=None, fail_silently=False):
    """
    Plain-text email for internal admin/error notifications.
    """
    _django_send_mail(
        subject=subject,
        message=message,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=fail_silently,
    )


def send_html_email(subject, html_content, recipient_list, from_email=None, fail_silently=False, attachments=None):
    """
    HTML email with auto-generated plain-text fallback.

    Args:
        attachments: list of (filename, content, mimetype) tuples, e.g. for PDF
    """
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(
        subject,
        text_content,
        from_email or settings.DEFAULT_FROM_EMAIL,
        recipient_list,
    )
    msg.attach_alternative(html_content, "text/html")
    if attachments:
        for filename, content, mimetype in attachments:
            msg.attach(filename, content, mimetype)
    msg.send(fail_silently=fail_silently)


def collect_recipients(*emails):
    """
    Collect unique, non-empty email addresses.
    Each argument can be a single address or a comma-separated string (or None).
    Preserves order and removes duplicates.
    """
    seen = set()
    result = []
    for addr in emails:
        if not addr:
            continue
        for part in str(addr).split(','):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                result.append(part)
    return result


def send_template_email(subject, template_name, context, recipient_list, from_email=None,
                        fail_silently=False, attachments=None, request=None):
    """
    Render an HTML email template and send it.

    Args:
        template_name: short name (e.g. 'html_email-confirmation.html') or full path
        context:       template context dict
        attachments:   list of (filename, content, mimetype) tuples
        request:       Django request for template rendering context (optional)
    """
    from basecamp.basecamp_utils import render_email_template
    html_content = render_email_template(template_name, context, request=request)
    send_html_email(subject, html_content, recipient_list, from_email=from_email,
                    fail_silently=fail_silently, attachments=attachments)