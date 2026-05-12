from django.apps import AppConfig


class ClicNLocalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clic_n_local_app'
    verbose_name = "Boutique"

    def ready(self):
        import clic_n_local_app.signals
