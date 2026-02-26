from datetime import datetime, date, timedelta

import logging
import requests
import stripe
import json 

from django.conf import settings
from csp.constants import NONCE
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.utils import timezone

from main.settings import RECIPIENT_EMAIL, DEFAULT_FROM_EMAIL
from blog.models import Post, Inquiry, PaypalPayment, StripePayment, Driver
from blog.tasks import send_confirm_email
from blog.sms_utils import send_sms_notice, send_whatsapp_template
from basecamp.area import get_suburbs
from basecamp.area_full import get_more_suburbs
from basecamp.area_home import get_home_suburbs
from basecamp.area_zones import area_zones

from .utils import (
    is_ajax, parse_date, handle_email_sending, format_pickup_time_12h,
    render_to_pdf, add_bag, to_int, to_bool, safe_float,
    handle_checkout_session_completed, paypal_ipn_error_email, get_sorted_suburbs,
    verify_turnstile, render_email_template
)

logger = logging.getLogger(__name__)


