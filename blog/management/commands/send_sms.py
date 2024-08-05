import os
from twilio.rest import Client
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from blog.models import Post

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Command(BaseCommand):
    help = 'Send final notices'

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        final_notices = Post.objects.filter(pickup_date=tomorrow)
        
        # Initialize Twilio client once
        account_sid = 'AC9ad86a3cd3fc22fa11c35d8d17bde7a0'
        auth_token = '632142d0e5afac3e05359e87abe61d2a'
        client = Client(account_sid, auth_token)

        def sms_one(sendto):
            client.messages.create(
                body="EasyGo - Urgent notice \
                      \n\nWe haven't received your payment and a response to our emails. \
                      \nPlease contact us ASAP or your booking may be canceled. \
                      \nReply only via email >> info@easygoshuttle.com.au",
                from_='+61488885330',
                to=sendto
            )

        for final_notice in final_notices:
            if not final_notice.reminder and not final_notice.cancelled and not final_notice.paid:
                sms_contact = final_notice.contact  
                if sms_contact:
                    sms_one(sms_contact)

        self.stdout.write(self.style.SUCCESS('Successfully sent final notices via SMS'))
