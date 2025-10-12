from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # importa y registra los signals del módulo notifications_mobile
        import api.notifications_mobile.signals_consulta  # noqa: F401
