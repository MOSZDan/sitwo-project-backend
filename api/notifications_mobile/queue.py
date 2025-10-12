from typing import Optional, Mapping, Any, Iterable
from django.utils import timezone
from django.db import transaction
from .models import (
    HistorialNotificacionMN,
    TipoNotificacionMN,
    CanalNotificacionMN,
    DispositivoMovilMN,
)

DEFAULT_CANAL = "PUSH_MOBILE"

def _ensure_catalog(nombre_tipo: str, canal_nombre: str = DEFAULT_CANAL):
    tipo, _ = TipoNotificacionMN.objects.get_or_create(
        nombre=nombre_tipo,
        defaults={"descripcion": nombre_tipo, "activo": True},
    )
    canal, _ = CanalNotificacionMN.objects.get_or_create(
        nombre=canal_nombre,
        defaults={"descripcion": "Canal push móvil", "activo": True},
    )
    return tipo, canal

@transaction.atomic
def enqueue_notif(
    *,
    usuario_codigo: int,
    titulo: str,
    mensaje: str,
    tipo_nombre: str,
    data: Optional[Mapping[str, Any]] = None,
    iddispositivomovil: Optional[int] = None,
) -> HistorialNotificacionMN:
    """
    Encola UNA notificación (fila en historialnotificacion).
    Si iddispositivomovil es None, queda a nivel usuario (varios tokens posibles).
    """
    tipo, canal = _ensure_catalog(tipo_nombre, DEFAULT_CANAL)
    h = HistorialNotificacionMN.objects.create(
        titulo=titulo,
        mensaje=mensaje,
        datos_adicionales=dict(data or {}),
        estado="PENDING",
        fecha_creacion=timezone.now(),
        fecha_envio=None,
        fecha_entrega=None,
        fecha_lectura=None,
        error_mensaje=None,
        intentos=0,
        codusuario=usuario_codigo,
        idtiponotificacion=tipo.id,
        idcanalnotificacion=canal.id,
        iddispositivomovil=iddispositivomovil,
    )
    return h

@transaction.atomic
def enqueue_notif_for_user_devices(
    *,
    usuario_codigo: int,
    titulo: str,
    mensaje: str,
    tipo_nombre: str,
    data: Optional[Mapping[str, Any]] = None,
) -> list[HistorialNotificacionMN]:
    """
    Encola una notificación POR CADA dispositivo activo del usuario,
    seteando iddispositivomovil en cada fila.
    """
    tipo, canal = _ensure_catalog(tipo_nombre, DEFAULT_CANAL)
    dispositivos: Iterable[DispositivoMovilMN] = DispositivoMovilMN.objects.filter(
        codusuario=usuario_codigo, activo=True
    ).only("id")
    rows: list[HistorialNotificacionMN] = []
    now = timezone.now()

    for d in dispositivos:
        rows.append(HistorialNotificacionMN(
            titulo=titulo,
            mensaje=mensaje,
            datos_adicionales=dict(data or {}),
            estado="PENDING",
            fecha_creacion=now,
            fecha_envio=None,
            fecha_entrega=None,
            fecha_lectura=None,
            error_mensaje=None,
            intentos=0,
            codusuario=usuario_codigo,
            idtiponotificacion=tipo.id,
            idcanalnotificacion=canal.id,
            iddispositivomovil=d.id,
        ))
    if rows:
        HistorialNotificacionMN.objects.bulk_create(rows, batch_size=500)
    return rows
