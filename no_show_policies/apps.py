from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class NoShowPoliciesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "no_show_policies"

    def ready(self):
        # Cargar el módulo de señales cuando la app esté lista
        try:
            from . import signals  # noqa: F401
            logger.info("NoShowPolicies: módulo de señales importado en ready().")
        except Exception as e:
            # No falles el arranque por esto; deja un log claro
            logger.warning("NoShowPolicies: no se pudo importar signals en ready(): %s", e)