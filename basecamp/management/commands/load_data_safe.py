from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models.signals import post_save, pre_save


class Command(BaseCommand):
    help = 'Run loaddata with all blog/articles signals disconnected'

    def add_arguments(self, parser):
        parser.add_argument('fixtures', nargs='+', help='Fixture labels')
        parser.add_argument('--database', default=None, dest='database')
        parser.add_argument('--app', default=None, dest='app_label')
        parser.add_argument('--ignorenonexistent', '-i', action='store_true', dest='ignore')
        parser.add_argument('--exclude', '-e', action='append', default=[], dest='exclude')
        parser.add_argument('--format', default=None, dest='format')

    def handle(self, *args, **options):
        from blog.models import Post as BlogPost, Inquiry, PaypalPayment, StripePayment
        from articles.models import Post as ArticlesPost
        import blog.signals as blog_signals
        import articles.signals as articles_signals

        # (signal, receiver_func, sender_model, dispatch_uid or None)
        # dispatch_uid가 있으면 Django는 uid로 룩업하므로 receiver는 무시됨.
        # dispatch_uid가 없으면 receiver 함수 id로 룩업.
        SIGNALS = [
            # --- blog/signals.py ---
            (pre_save,  blog_signals.reset_driver_calendar_event_id,     BlogPost,       'reset_driver_calendar_event_id_once'),
            (post_save, blog_signals.notify_user_inquiry,                 Inquiry,        'notify_user_inquiry_once'),
            (post_save, blog_signals.notify_user_post,                    BlogPost,       'notify_user_post_once'),
            (post_save, blog_signals.notify_user_post_cancelled,          BlogPost,       'notify_user_post_cancelled_once'),
            (post_save, blog_signals.set_prepay_for_foreign_users,        BlogPost,       'set_prepay_for_foreign_users'),
            (post_save, blog_signals.async_create_event_on_calendar,      BlogPost,       'async_create_event_on_calendar_once'),
            (post_save, blog_signals.check_missing_info,                  BlogPost,       'check_missing_info_once'),
            (post_save, blog_signals.close_bird_mapping_on_no_driver,     BlogPost,       'close_bird_mapping_on_no_driver_once'),
            (post_save, blog_signals.async_notify_user_payment_paypal,    PaypalPayment,  'async_notify_user_payment_paypal_once'),
            (post_save, blog_signals.async_notify_user_payment_stripe,    StripePayment,  'async_notify_user_payment_stripe_once'),
            (post_save, blog_signals.update_sitemap_from_blog,            ArticlesPost,   None),
            # --- articles/signals.py ---
            (post_save, articles_signals.regenerate_sitemap_on_publish,   ArticlesPost,   None),
            (post_save, articles_signals.auto_fetch_thumbnail,            ArticlesPost,   None),
            (post_save, articles_signals.trigger_gmb_posting,             ArticlesPost,   None),
        ]

        self.stdout.write('Disconnecting signals...')
        for signal, receiver, sender, uid in SIGNALS:
            disconnected = signal.disconnect(receiver=receiver, sender=sender, dispatch_uid=uid)
            label = uid if uid else receiver.__name__
            status = self.style.SUCCESS('OK') if disconnected else self.style.WARNING('NOT FOUND')
            self.stdout.write(f'  [{status}] {label}')

        fixtures = options['fixtures']
        self.stdout.write(f'\nLoading: {", ".join(fixtures)}')

        loaddata_kwargs = {}
        if options.get('database'):
            loaddata_kwargs['database'] = options['database']
        if options.get('app_label'):
            loaddata_kwargs['app_label'] = options['app_label']
        if options.get('ignore'):
            loaddata_kwargs['ignorenonexistent'] = True
        if options.get('exclude'):
            loaddata_kwargs['exclude'] = options['exclude']
        if options.get('format'):
            loaddata_kwargs['format'] = options['format']

        call_command('loaddata', *fixtures, **loaddata_kwargs)

        self.stdout.write(self.style.SUCCESS('\nDone. loaddata completed with all signals disabled.'))
