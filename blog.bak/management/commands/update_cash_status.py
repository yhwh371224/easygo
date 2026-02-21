import os
import threading
from django.core.management.base import BaseCommand
from blog.models import Post
from retrieve_cash import main as get_cash_emails_list 


class Command(BaseCommand):
    help = 'Update the cash status for posts based on "cash" labeled emails (using retrieve_cash.py).'

    def __init__(self):
        self.lock = threading.Lock()
        super().__init__()

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Fetching cash-related emails from Gmail API via retrieve_cash.py..."))
        
        # retrieve_cash.py 파일의 main 함수를 호출
        my_list = get_cash_emails_list() 
        
        if not my_list:
            self.stdout.write(self.style.WARNING("No cash-related emails found. Exiting."))
            return

        unique_emails = set(my_list)
        
        updated_count = 0

        self.stdout.write(self.style.NOTICE(f"Found {len(unique_emails)} unique emails to process."))

        with self.lock:

            all_posts = Post.objects.all()

            for list_email in unique_emails:

                for post in all_posts:
                    
                    if post.email.lower() == list_email and not post.cash:
                        
                        try:
                            post.cash = True
                            post.reminder = True
                            post.pending = False
                            post.cancelled = False

                            # 필드 변경 사항을 DB에 저장합니다.
                            post.save(update_fields=['cash', 'reminder', 'pending', 'cancelled']) 
                            updated_count += 1
                            
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Updated post (ID: {post.pk}) to cash=True for email: {list_email}"
                                )
                            )
                        
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error saving post ID {post.pk}: {e}"))
                
        self.stdout.write(
            self.style.SUCCESS(
                f"\n--- Total Update Complete ---"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Total {updated_count} Post records were individually updated to cash=True."
            )
        )