from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # Import des signaux pour qu'ils soient connectés au démarrage de Django.
        # Sans ce ready(), les @receiver(post_save, ...) ne sont JAMAIS exécutés
        # (bug silencieux : ni email, ni notif déclenchés par changement de statut).
        from . import signals  # noqa: F401
