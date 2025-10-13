from datetime import timedelta
import logging

from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from .models import PoliticaNoShow, Multa
from api.models import BloqueoUsuario  # tabla de bloqueos (en app api)

logger = logging.getLogger(__name__)


def _get_usuario_from_consulta(consulta):
    """
    Según tu modelo, el 'dueño' de la consulta es el paciente.
    consulta.codpaciente -> api.Paciente
    paciente.codusuario  -> api.Usuario
    """
    try:
        paciente = getattr(consulta, "codpaciente", None)
        if not paciente:
            return None
        return getattr(paciente, "codusuario", None)
    except Exception:
        return None


def _get_empresa_id(consulta, usuario):
    """
    Prioriza empresa de la consulta; si no, la del usuario.
    """
    eid = getattr(consulta, "empresa_id", None)
    if eid:
        return int(eid)
    if usuario:
        eid = getattr(usuario, "empresa_id", None)
        if eid:
            return int(eid)
    return None


@transaction.atomic
def aplicar_politicas_para_estado(consulta, nuevo_estado_id):
    """
    Aplica políticas activas para (empresa, estado_consulta) cuando una consulta cambia de estado.
    - Crea Multa (única por consulta/política).
    - Crea o extiende BloqueoUsuario si corresponde.
    """
    usuario = _get_usuario_from_consulta(consulta)
    if not usuario:
        logger.info("NoShowPolicies: no se pudo resolver usuario desde consulta id=%s", getattr(consulta, "id", None))
        return

    empresa_id = _get_empresa_id(consulta, usuario)
    if not empresa_id:
        logger.info("NoShowPolicies: no se pudo resolver empresa para consulta id=%s", getattr(consulta, "id", None))
        return

    politicas = PoliticaNoShow.objects.filter(
        activo=True,
        empresa_id=empresa_id,
        estado_consulta_id=nuevo_estado_id,
    )

    if not politicas.exists():
        return

    ahora = timezone.now()

    for p in politicas:
        # 1) Multa económica
        monto = p.penalizacion_economica or 0
        if float(monto) > 0:
            Multa.objects.get_or_create(
                consulta=consulta,
                politica=p,
                defaults={
                    "empresa_id": empresa_id,
                    "usuario": usuario,
                    "monto": monto,
                    "motivo": f"Aplicación automática por política #{p.pk} (estado_id={nuevo_estado_id})"[:255],
                    "estado": "pendiente",
                },
            )

        # 2) Bloqueo temporal (si está activo y con días > 0)
        if p.bloqueo_temporal and (p.dias_bloqueo or 0) > 0:
            hasta = ahora + timedelta(days=int(p.dias_bloqueo))

            # Evitar duplicar bloqueos superpuestos: si hay uno activo, extenderlo si el nuevo fin es mayor.
            bloqueo_vigente = (
                BloqueoUsuario.objects
                .filter(usuario=usuario, activo=True)
                .filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gt=ahora))
                .order_by("-fecha_inicio")
                .first()
            )

            motivo = f"Bloqueo automático por política #{p.pk} durante {p.dias_bloqueo} días."
            if bloqueo_vigente:
                # Si el existente termina antes que el nuevo, extiende
                fin_actual = bloqueo_vigente.fecha_fin
                if fin_actual is None or fin_actual < hasta:
                    bloqueo_vigente.fecha_fin = hasta
                    if not bloqueo_vigente.motivo:
                        bloqueo_vigente.motivo = motivo
                    bloqueo_vigente.save(update_fields=["fecha_fin", "motivo"])
            else:
                BloqueoUsuario.objects.create(
                    usuario=usuario,
                    fecha_inicio=ahora,
                    fecha_fin=hasta,
                    motivo=motivo,
                    activo=True,
                    # creado_por: opcional, se puede setear desde vistas/admin si aplica
                )