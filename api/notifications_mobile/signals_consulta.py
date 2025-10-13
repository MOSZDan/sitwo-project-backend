# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    ConsultaMN,            # fallback unmanaged
    HorarioMN,
    UsuarioMN,
    HistorialNotificacionMN,
    DispositivoMovilMN,    # <-- AGREGAR ESTA LÍNEA
)

log = logging.getLogger("signals_consulta")

# ---- elegir el sender real (la clase de modelo con la que guardas la cita) ----
def _pick_consulta_sender():
    # 1) intenta la clase administrada que usas en tus views: api.Consulta
    try:
        m = apps.get_model("api", "Consulta")
        if m is not None:
            return m
    except Exception:
        pass
    # 2) busca por db_table == "consulta"
    try:
        for m in apps.get_models():
            if (getattr(getattr(m, "_meta", None), "db_table", "") or "").lower() == "consulta":
                return m
    except Exception:
        pass
    # 3) último recurso: nuestra clase unmanaged
    return ConsultaMN

ConsultaSender = _pick_consulta_sender()
log.info("signals_consulta: hook activo sobre sender=%s (table=%s)",
         getattr(ConsultaSender, "__name__", str(ConsultaSender)),
         getattr(getattr(ConsultaSender, "_meta", None), "db_table", "?"))


def _as_int_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return int(value)
        except Exception:
            return None
    for attr in ("pk", "id", "codigo", "codusuario"):
        try:
            if hasattr(value, attr):
                v = getattr(value, attr)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return int(v)
        except Exception:
            pass
    try:
        return int(str(value))
    except Exception:
        return None


def _usuario_codigo_from_instance(instance) -> Optional[int]:
    for base in ("codpaciente", "usuario", "paciente", "cliente", "owner", "codusuario"):
        attr_id = f"{base}_id"
        if hasattr(instance, attr_id):
            code = _as_int_id(getattr(instance, attr_id))
            if code:
                return code
        if hasattr(instance, base):
            code = _as_int_id(getattr(instance, base))
            if code:
                return code
    return None


def _resolve_empresa_id(instance) -> Optional[int]:
    emp = _as_int_id(getattr(instance, "empresa_id", None))
    if emp:
        return emp

    cod = _usuario_codigo_from_instance(instance)
    if cod:
        emp = UsuarioMN.objects.filter(codigo=cod).values_list("empresa_id", flat=True).first()
        emp = _as_int_id(emp)
        if emp:
            return emp

    for base in ("cododontologo", "odontologo"):
        attr_id = f"{base}_id"
        cod_od = None
        if hasattr(instance, attr_id):
            cod_od = _as_int_id(getattr(instance, attr_id))
        elif hasattr(instance, base):
            cod_od = _as_int_id(getattr(instance, base))
        if cod_od:
            emp = UsuarioMN.objects.filter(codigo=cod_od).values_list("empresa_id", flat=True).first()
            emp = _as_int_id(emp)
            if emp:
                return emp
    return None


def _cita_datetime(fecha, idhorario_value) -> Optional[datetime]:
    hid = _as_int_id(idhorario_value)
    if not (fecha and hid):
        return None
    try:
        h = HorarioMN.objects.only("hora").get(id=hid)
    except Exception:
        log.exception("signals_consulta: no se pudo resolver hora para idhorario=%s", idhorario_value)
        return None
    dt = datetime.combine(fecha, h.hora)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt


def _pick_device_id(codusuario: int) -> Optional[int]:
    """
    Devuelve el id del dispositivo ACTIVO más reciente del usuario (con token válido).
    """
    return (
        DispositivoMovilMN.objects
        .filter(codusuario=codusuario, activo=True)
        .exclude(token_fcm__isnull=True)
        .exclude(token_fcm="")
        .order_by("-ultima_actividad", "-fecha_registro", "-id")
        .values_list("id", flat=True)
        .first()
    )


def _enqueue(
    codusuario: int,
    titulo: str,
    mensaje: str,
    fecha_envio: datetime,
    *,
    empresa_id: Optional[int],
    consulta_id: Optional[int],
    tipo: int = 1,       # 1 = CONSULTA
    canal: int = 1,      # 1 = PUSH
    datos_extra: Optional[dict] = None,
) -> None:
    cod = _as_int_id(codusuario)
    if not cod:
        log.warning("signals_consulta: _enqueue sin codusuario válido (=%r)", codusuario)
        return

    # único dispositivo activo por usuario => lo resolvemos aquí
    device_id = (
        DispositivoMovilMN.objects
        .filter(codusuario=cod, activo=True)
        .order_by("-ultima_actividad")
        .values_list("id", flat=True)
        .first()
    )

    datos = {"consulta_id": consulta_id, "empresa_id": empresa_id}
    if datos_extra:
        datos.update(datos_extra)

    HistorialNotificacionMN.objects.create(
        titulo=titulo,
        mensaje=mensaje,
        datos_adicionales=datos,
        estado="PENDIENTE",
        fecha_creacion=timezone.now(),
        fecha_envio=fecha_envio,
        fecha_entrega=None,
        fecha_lectura=None,
        error_mensaje=None,
        intentos=0,
        codusuario=cod,
        idtiponotificacion=tipo,
        idcanalnotificacion=canal,
        iddispositivomovil=device_id,   # <<< ahora se guarda
    )


@receiver(post_save, sender=ConsultaSender, dispatch_uid="mn_consulta_created_queue_v3")
def _handler(sender, instance, created: bool, **kwargs):
    if not created:
        return
    try:
        usuario_codigo = _as_int_id(_usuario_codigo_from_instance(instance))
        if not usuario_codigo:
            log.info("signals_consulta: consulta id=%s sin usuario_codigo; no se encola.",
                     getattr(instance, "id", None))
            return

        empresa_id = _resolve_empresa_id(instance)

        fecha = getattr(instance, "fecha", None)
        idhorario_val = (
            getattr(instance, "idhorario_id", None)
            or getattr(instance, "idhorario", None)
            or getattr(instance, "horario_id", None)
            or getattr(instance, "horario", None)
        )
        cita_dt = _cita_datetime(fecha, idhorario_val) if fecha else None

        # Confirmación inmediata
        body = f"Tu consulta fue creada para {fecha:%d/%m}" if fecha else "Tu consulta fue creada."
        _enqueue(
            codusuario=usuario_codigo,
            titulo="Consulta creada",
            mensaje=body,
            fecha_envio=timezone.now(),
            empresa_id=empresa_id,
            consulta_id=getattr(instance, "id", None),
        )

        # Recordatorios (24h y 2h antes) si tenemos fecha+hora
        if cita_dt:
            now = timezone.now()
            for delta, label in ((timedelta(hours=24), "24h"), (timedelta(hours=2), "2h")):
                when = cita_dt - delta
                if when > now:
                    _enqueue(
                        codusuario=usuario_codigo,
                        titulo="Recordatorio de consulta",
                        mensaje=f"Tienes una consulta el {cita_dt:%d/%m %H:%M}. Recordatorio {label}.",
                        fecha_envio=when,
                        empresa_id=empresa_id,
                        consulta_id=getattr(instance, "id", None),
                        datos_extra={"reminder": label},
                    )
    except Exception:
        log.exception("signals_consulta: error encolando notificaciones")
