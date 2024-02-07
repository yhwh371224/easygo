from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'

    def ready(self):
        # from django.db.backends.signals import connection_created        
        # from blog import tasks        
        import blog.signals        
        # connection_created.connect(tasks.handle_database_change)


