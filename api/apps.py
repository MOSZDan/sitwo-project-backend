# api/apps.py
from django.apps import AppConfig
import sys

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """
        Se ejecuta cuando la app está lista.
        Si estamos en modo 'test', modifica todos los modelos de esta app
        para que Django los gestione y cree sus tablas en la BD de prueba.
        """
        if 'test' in sys.argv:
            for model in self.get_models():
                model._meta.managed = True
