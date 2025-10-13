from django.db import transaction
from django.utils import timezone

from .models import CanalNotificacionMN, TipoNotificacionMN

PUSH_CHANNEL_NAME = "PUSH"
DEFAULT_TYPES = [
    "CITA_REGISTRADA",
    "CITA_CONFIRMADA",
    "CITA_CANCELADA",
    "REMINDER_H24",
    "REMINDER_H2",
]

@transaction.atomic
def ensure_channel_and_types() -> tuple[int, dict[str, int]]:
    # Canal
    try:
        canal = CanalNotificacionMN.objects.get(nombre=PUSH_CHANNEL_NAME)
    except CanalNotificacionMN.DoesNotExist:
        canal = CanalNotificacionMN(nombre=PUSH_CHANNEL_NAME, descripcion="Canal de notificaciones push", activo=True)
        # save sin migrations (managed=False) funciona igual:
        canal.save(force_insert=True)
    canal_id = canal.id

    # Tipos
    tipos_ids: dict[str, int] = {}
    for name in DEFAULT_TYPES:
        try:
            t = TipoNotificacionMN.objects.get(nombre=name)
        except TipoNotificacionMN.DoesNotExist:
            t = TipoNotificacionMN(nombre=name, descripcion="", activo=True)
            t.save(force_insert=True)
        tipos_ids[name] = t.id

    return canal_id, tipos_ids
