import logging
from django.apps import apps
from django.db.models.signals import pre_save

from .services import aplicar_politicas_para_estado

logger = logging.getLogger(__name__)


def _connect_consulta_signal():
    """
    Conecta pre_save de api.Consulta para detectar cambio en 'idestadoconsulta'.
    """
    Consulta = apps.get_model("api", "Consulta")
    if Consulta is None:
        logger.warning("NoShowPolicies: Modelo api.Consulta no encontrado. Señales NO conectadas.")
        return

    def handler(sender, instance, **kwargs):
        # Solo al actualizar (si ya existe en BD)
        if not instance.pk:
            return

        try:
            anterior = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return

        prev_estado_id = getattr(anterior, "idestadoconsulta_id", None)
        new_estado_id = getattr(instance, "idestadoconsulta_id", None)

        if new_estado_id and new_estado_id != prev_estado_id:
            try:
                aplicar_politicas_para_estado(instance, new_estado_id)
            except Exception as e:
                logger.exception("NoShowPolicies: error aplicando políticas para consulta id=%s: %s",
                                 getattr(instance, "id", None), e)

    pre_save.connect(handler, sender=Consulta, weak=False)
    logger.info("NoShowPolicies: señales conectadas para api.Consulta (pre_save, campo idestadoconsulta).")


# Conectar en import (apps.py.ready() ya importa este módulo)
_connect_consulta_signal()