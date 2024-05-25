from django.apps import AppConfig


class EasygoReviewConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'easygo_review'

    def ready(self):
        import easygo_review.signals
