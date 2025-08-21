from django.core.management.base import BaseCommand
from blog.models import Post


class Command(BaseCommand):    

    def handle(self, *args, **options):
        target_email = "kate@diveplanit.com"
        new_email = "heather@blueplanetdc.com"
        new_contact = "+12404819639"

        posts = Post.objects.filter(email__iexact=target_email)

        count = 0
        for post in posts:
            if not post.email1:
                post.email1 = target_email
            post.email = new_email
            post.contact = new_contact
            post.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} posts updated."))

# python manage.py shell 
from blog.models import Post

Post.objects.filter(email="silvio.vichroski@fiero.org.br").update(email="sungkam718@gmail.com")
Post.objects.filter(email="sungkam3@gmail.com").update(email="kate@diveplanit.com")
Post.objects.filter(email="heather@blueplanetdc.com").update(email="kate@diveplanit.com")
Post.objects.filter(email="kate@diveplanit.com").update(email="sungkam3@gmail.com")
Post.objects.filter(email="kate@diveplanit.com").update(name="Kate Smillie")
Post.objects.filter(email="heather@blueplanetdc.com").update(name="")


from blog.models import Post, PaypalPayment
from blog.tasks import notify_user_payment_paypal

name = "Sung Kam"
email = "sungkam718@gmail.com"
amount = "412" 

payment = PaypalPayment.objects.create(name=name, email=email, amount=amount)

notify_user_payment_paypal(payment.id)

from blog.models import Post, StripePayment
from blog.tasks import notify_user_payment_stripe

name = "sung kam"
email = "sungkam3@gmail.com"
amount = "280"  

payment = StripePayment.objects.create(name=name, email=email, amount=amount)

notify_user_payment_stripe(payment.id)
