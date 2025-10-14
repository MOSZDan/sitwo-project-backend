from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils.timezone import make_aware
from django.utils import timezone  # <-- necesario (usado en reprogramar)
from datetime import datetime, timedelta
import csv
from io import BytesIO

from rest_framework import status, serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets, mixins
from rest_framework.viewsets import GenericViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Paciente, Consulta, Odontologo, Horario, Tipodeconsulta, Estadodeconsulta,  # <-- añadido Estadodeconsulta
    Usuario, Tipodeusuario, Bitacora, Historialclinico, Consentimiento
)

from .serializers import (
    PacienteSerializer,
    ConsultaSerializer,
    CreateConsultaSerializer,
    OdontologoMiniSerializer,
    HorarioSerializer,
    TipodeconsultaSerializer,
    UpdateConsultaSerializer,
    UsuarioAdminSerializer,
    TipodeusuarioSerializer,
    BitacoraSerializer,
    ReprogramarConsultaSerializer,
    HistorialclinicoCreateSerializer,
    HistorialclinicoListSerializer,
    ConsentimientoSerializer,
    EstadodeconsultaSerializer,  # <-- añadido
)


# -------------------- Health / Utils --------------------

def health(request):
    """
    Ping de salud - Endpoint compatible con load balancers.
    Retorna 200 OK siempre para health checks.
    Muestra información del tenant detectado si está disponible.
    """
    tenant = getattr(request, 'tenant', None)

    response_data = {
        "ok": True,
        "status": "healthy",
        "tenant_detected": tenant is not None,
    }

    if tenant:
        response_data["tenant"] = {
            "id": tenant.id,
            "nombre": tenant.nombre,
            "subdomain": tenant.subdomain,
            "activo": tenant.activo,
        }
    else:
        response_data["message"] = "No se detectó ningún tenant (health check mode)"

    return JsonResponse(response_data, status=200)


def db_health(request):
    """Diagnóstico de conexión a base de datos"""
    from django.db import connection
    import os

    try:
        # Intentar una consulta simple
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        db_status = "OK"
        error_msg = None
    except Exception as e:
        db_status = "ERROR"
        error_msg = str(e)

    return JsonResponse({
        "database_status": db_status,
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "database_engine": connection.settings_dict.get('ENGINE', 'Unknown'),
        "database_name": connection.settings_dict.get('NAME', 'Unknown'),
        "database_host": connection.settings_dict.get('HOST', 'Unknown'),
        "database_port": connection.settings_dict.get('PORT', 'Unknown'),
        "error": error_msg
    })


def db_info(request):
    """Info rápida de la conexión a DB (útil en dev/diagnóstico)."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version()")
            db, user, version = cur.fetchone()

        # Cerrar conexión explícitamente
        connection.close()

        return JsonResponse({
            "database": db,
            "user": user,
            "version": version[:50],  # Limitar longitud
            "status": "connected"
        })
    except Exception as e:
        # Cerrar conexión en caso de error
        try:
            connection.close()
        except:
            pass

        return JsonResponse({
            "error": str(e),
            "status": "error"
        }, status=500)


def users_count(request):
    """
    Cuenta de usuarios de la tabla Usuario (modelo de negocio).
    Filtra por empresa (multi-tenancy).
    NOTA: devolvemos 'count' para cuadrar con el frontend.
    """
    queryset = Usuario.objects.all()

    # Filtrar por tenant si está disponible
    if hasattr(request, 'tenant') and request.tenant:
        queryset = queryset.filter(empresa=request.tenant)

    return JsonResponse({"count": queryset.count()})


# Helper reutilizable: ¿el usuario actual es admin en la tabla de negocio?
def _tenant(request):
    """Obtiene el tenant desde el middleware (request.tenant o None)."""
    return getattr(request, "tenant", None)


def _es_admin_por_tabla(request) -> bool:
    """
    ¿El usuario autenticado es rol 'Administrador' EN SU EMPRESA?
    Compara por nombre de rol (no por id) y misma empresa que el tenant.
    """
    t = _tenant(request)
    if not t or not request.user or not request.user.is_authenticated:
        return False

    email = (getattr(request.user, "email", None) or getattr(request.user, "username", "")).strip().lower()
    if not email:
        return False
    try:
        u = Usuario.objects.select_related("idtipousuario").get(correoelectronico__iexact=email)
    except Usuario.DoesNotExist:
        return False

    return (
            u.empresa_id == t.id and
            u.idtipousuario is not None and
            (u.idtipousuario.rol or "").strip().lower() == "administrador"
    )


# -------------------- Pacientes --------------------

class PacienteViewSet(ReadOnlyModelViewSet):
    """
    API read-only de Pacientes.
    Solo devuelve pacientes cuyo usuario tiene rol id=2 Y pertenecen a la empresa del tenant.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PacienteSerializer

    def get_queryset(self):
        """Filtra pacientes por empresa (multi-tenancy)"""
        queryset = (
            Paciente.objects
            .select_related("codusuario")
            .filter(codusuario__idtipousuario_id=2)
        )

        # Filtrar por tenant si está disponible
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        return queryset


# -------------------- Consultas (Citas) --------------------

class ConsultaViewSet(ModelViewSet):
    """
    API para Consultas. Permite crear, leer, actualizar y eliminar.
    Filtrado por tenant (multi-tenancy).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConsultaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['codpaciente', 'fecha']

    def get_queryset(self):
        """Filtra consultas por empresa (multi-tenancy)"""
        queryset = Consulta.objects.select_related(
            "codpaciente__codusuario",
            "cododontologo__codusuario",
            "codrecepcionista__codusuario",
            "idhorario",
            "idtipoconsulta",
            "idestadoconsulta",
        )

        # Filtrar por tenant si está disponible
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        return queryset

    def perform_create(self, serializer):
        """Asigna automáticamente la empresa del tenant al crear una consulta"""
        # Asignar empresa del tenant
        if hasattr(self.request, 'tenant') and self.request.tenant:
            serializer.save(empresa=self.request.tenant)
        else:
            serializer.save()

        # Enviar email de confirmación (código existente)
        consulta = serializer.instance
        paciente = consulta.codpaciente
        usuario_paciente = paciente.codusuario

        if getattr(usuario_paciente, "notificaciones_email", False):
            try:
                subject = "Confirmación de tu cita en Clínica Dental"
                fecha_formateada = consulta.fecha.strftime('%d de %B de %Y')
                hora_formateada = consulta.idhorario.hora.strftime('%H:%M')

                message = f"""
Hola {usuario_paciente.nombre},

Tu cita ha sido agendada exitosamente con los siguientes detalles:

📅 Fecha: {fecha_formateada}
🕐 Hora: {hora_formateada}
👨‍⚕️ Odontólogo: Dr. {consulta.cododontologo.codusuario.nombre} {consulta.cododontologo.codusuario.apellido}
🦷 Tipo de consulta: {consulta.idtipoconsulta.nombreconsulta}

Recuerda llegar 15 minutos antes de tu cita.

¡Te esperamos en Smile Studio!

Si necesitas cancelar o reprogramar tu cita, ponte en contacto con nosotros.
                """

                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [usuario_paciente.correoelectronico]
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)

            except Exception as e:
                print(f"Error al enviar correo de notificación: {e}")

    def get_serializer_class(self):
        # --- MODIFICACIÓN: Añadir el nuevo serializador ---
        if self.action == 'reprogramar':
            return ReprogramarConsultaSerializer
        if self.action in ["create", "update"]:
            return CreateConsultaSerializer
        if self.action == "partial_update":
            return UpdateConsultaSerializer
        return ConsultaSerializer

    @action(detail=True, methods=['patch'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        """
        Reprograma una cita a una nueva fecha y/o horario.
        Valida que el nuevo horario esté libre.
        """
        consulta = self.get_object()

        # Pasamos la instancia de la consulta al contexto del serializador para la validación
        serializer = self.get_serializer(data=request.data, context={'consulta': consulta})
        serializer.is_valid(raise_exception=True)

        nueva_fecha = serializer.validated_data['fecha']
        nuevo_horario = serializer.validated_data['idhorario']

        # Actualizar la consulta
        consulta.fecha = nueva_fecha
        consulta.idhorario = nuevo_horario

        # Opcional: Cambiar estado a 'Reprogramada' si existe (ej. id=5)
        # consulta.idestadoconsulta_id = 5
        consulta.save()

        # Refrescar desde la BD para obtener todas las relaciones
        consulta.refresh_from_db()

        # 1) borrar pendientes anteriores de esta consulta
        try:
            HistorialNotificacionMN.objects.filter(
                estado="PENDIENTE",
                datos_adicionales__consulta_id=consulta.id
            ).delete()
        except Exception:
            pass  # No fallar si hay error con notificaciones

        # 2) (re)crear recordatorios 24h y 2h si hay fecha+hora
        try:
            cita_dt = None
            if consulta.fecha and consulta.idhorario and consulta.idhorario.hora:
                dt = datetime.combine(consulta.fecha, consulta.idhorario.hora)
                cita_dt = make_aware(dt) if timezone.is_naive(dt) else dt

            if cita_dt:
                # único dispositivo activo del paciente (para fijar id al encolar)
                device_id = (
                    DispositivoMovilMN.objects
                    .filter(codusuario=consulta.codpaciente.codusuario.codigo, activo=True)
                    .order_by("-ultima_actividad")
                    .values_list("id", flat=True)
                    .first()
                )

                def _mk(title, body, when, label):
                    HistorialNotificacionMN.objects.create(
                        titulo=title,
                        mensaje=body,
                        datos_adicionales={
                            "consulta_id": consulta.id,
                            "empresa_id": getattr(consulta, "empresa_id", None) or getattr(consulta.empresa, "id",
                                                                                           None),
                            "reminder": label,
                        },
                        estado="PENDIENTE",
                        fecha_creacion=timezone.now(),
                        fecha_envio=when,
                        fecha_entrega=None,
                        fecha_lectura=None,
                        error_mensaje=None,
                        intentos=0,
                        codusuario=consulta.codpaciente.codusuario.codigo,
                        idtiponotificacion=1,
                        idcanalnotificacion=1,
                        iddispositivomovil=device_id,
                    )

                now = timezone.now()
                for delta, label in ((timedelta(hours=24), "24h"), (timedelta(hours=2), "2h")):
                    when = cita_dt - delta
                    if when > now:
                        _mk(
                            "Recordatorio de consulta",
                            f"Tienes una consulta el {cita_dt:%d/%m %H:%M}. Recordatorio {label}.",
                            when,
                            label
                        )
        except Exception as e:
            print(f"Error al gestionar notificaciones móviles: {e}")

        # TODO: Considera enviar una notificación de reprogramación por email

        # Devolver la consulta completa actualizada con todas sus relaciones
        consulta_serializer = ConsultaSerializer(consulta)
        return Response(consulta_serializer.data, status=status.HTTP_200_OK)

    # --- NUEVA ACCIÓN: Cancelar Cita (eliminar definitivamente) ---
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """
        Cancela una cita eliminándola de la base de datos.
        Registra la cancelación en la bitácora antes de eliminar.
        """
        from datetime import date
        from .models import Bitacora, Usuario

        consulta = self.get_object()
        consulta_id = consulta.pk
        consulta_info = f"Cita #{consulta_id} - Paciente: {consulta.codpaciente.codusuario.nombre} {consulta.codpaciente.codusuario.apellido}"

        # Registrar en bitácora antes de eliminar
        try:
            usuario = None
            if request.user.is_authenticated:
                try:
                    usuario = Usuario.objects.get(correoelectronico=request.user.email)
                except Usuario.DoesNotExist:
                    pass

            from api.middleware import get_client_ip
            Bitacora.objects.create(
                accion='cancelar_cita',
                descripcion=f'Cita cancelada: {consulta_info}',
                usuario=usuario,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                modelo_afectado='Consulta',
                objeto_id=consulta_id,
                datos_adicionales={
                    'fecha': str(consulta.fecha),
                    'horario': consulta.idhorario.hora if consulta.idhorario else 'N/A',
                    'odontologo': f"{consulta.cododontologo.codusuario.nombre} {consulta.cododontologo.codusuario.apellido}" if consulta.cododontologo else 'N/A'
                }
            )
        except Exception as log_error:
            print(f"[Bitacora] No se pudo guardar el log de cancelación: {log_error}")

        # borrar recordatorios pendientes asociados a esta consulta
        try:
            HistorialNotificacionMN.objects.filter(
                estado="PENDIENTE",
                datos_adicionales__consulta_id=consulta.pk
            ).delete()
        except Exception:
            pass  # No fallar si hay error con notificaciones

        # Eliminar la cita
        consulta.delete()

        # TODO: Opcional - enviar notificación de cancelación por email

        return Response(
            {"ok": True, "detail": "La cita ha sido cancelada y eliminada.", "id": consulta_id},
            status=status.HTTP_200_OK
        )

    # --- NUEVA ACCIÓN: Eliminar citas vencidas automáticamente ---
    @action(detail=False, methods=['delete'], url_path='eliminar-vencidas')
    def eliminar_vencidas(self, request):
        """
        Elimina automáticamente todas las citas que ya pasaron de fecha.
        Esta función puede ser llamada desde el frontend o desde un cron job.
        """
        from datetime import date
        from .models import Bitacora, Usuario

        citas_vencidas = Consulta.objects.filter(fecha__lt=date.today())
        cantidad = citas_vencidas.count()

        if cantidad == 0:
            return Response(
                {"ok": True, "detail": "No hay citas vencidas para eliminar.", "cantidad": 0},
                status=status.HTTP_200_OK
            )

        # Registrar en bitácora
        try:
            usuario = None
            if request.user.is_authenticated:
                try:
                    usuario = Usuario.objects.get(correoelectronico=request.user.email)
                except Usuario.DoesNotExist:
                    pass

            from api.middleware import get_client_ip
            Bitacora.objects.create(
                accion='limpiar_citas_vencidas',
                descripcion=f'Eliminadas {cantidad} citas vencidas',
                usuario=usuario,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                modelo_afectado='Consulta',
                datos_adicionales={
                    'cantidad_eliminadas': cantidad,
                    'fecha_limpieza': str(date.today())
                }
            )
        except Exception as log_error:
            print(f"[Bitacora] No se pudo guardar el log de limpieza: {log_error}")

        # Eliminar todas las citas vencidas
        citas_vencidas.delete()

        return Response(
            {
                "ok": True,
                "detail": f"Se eliminaron {cantidad} citas vencidas.",
                "cantidad": cantidad
            },
            status=status.HTTP_200_OK
        )


# -------------------- Catálogos --------------------

class OdontologoViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OdontologoMiniSerializer

    def get_queryset(self):
        """Filtra odontólogos por empresa (multi-tenancy)"""
        queryset = Odontologo.objects.all()

        # Filtrar por tenant si está disponible
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        return queryset


class HorarioViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HorarioSerializer

    def get_queryset(self):
        """Filtra horarios por empresa (multi-tenancy)"""
        queryset = Horario.objects.all()

        # Filtrar por tenant si está disponible
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        return queryset

    @action(detail=False, methods=['get'], url_path='disponibles')
    def disponibles(self, request):
        import logging
        from datetime import datetime as dt

        logger = logging.getLogger(__name__)

        # 1. OBTENER PARÁMETROS
        fecha = request.query_params.get('fecha')
        odontologo_id = request.query_params.get('odontologo_id')
        # Log de parámetros recibidos
        logger.info(f"[Horarios Disponibles] Parámetros recibidos - fecha: '{fecha}', odontologo_id: '{odontologo_id}'")

        # Validar que existan los parámetros
        if not fecha or not odontologo_id:
            logger.warning(
                f"[Horarios Disponibles] Parámetros faltantes - fecha: {fecha}, odontologo_id: {odontologo_id}")
            return Response(
                {"detail": "Se requieren los parámetros 'fecha' y 'odontologo_id'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. VALIDAR FORMATO DE FECHA
        try:
            # Intentar parsear la fecha en formato YYYY-MM-DD
            fecha_obj = dt.strptime(fecha, '%Y-%m-%d').date()
            logger.info(f"[Horarios Disponibles] Fecha parseada correctamente: {fecha_obj}")
        except ValueError as e:
            logger.error(f"[Horarios Disponibles] Error al parsear fecha '{fecha}': {str(e)}")
            return Response(
                {
                    "detail": f"Formato de fecha inválido. Se esperaba YYYY-MM-DD pero se recibió '{fecha}'.",
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. VERIFICAR TENANT
        tenant_detected = hasattr(request, 'tenant') and request.tenant
        logger.info(f"[Horarios Disponibles] Tenant detectado: {tenant_detected}")
        if tenant_detected:
            logger.info(f"[Horarios Disponibles] Tenant: {request.tenant.nombre} (ID: {request.tenant.id})")
        else:
            logger.warning(f"[Horarios Disponibles] No se detectó tenant para el usuario: {request.user}")

        # 4. OBTENER HORARIOS DEL TENANT
        try:
            todos_horarios = self.get_queryset()
            count_horarios = todos_horarios.count()
            logger.info(f"[Horarios Disponibles] Total horarios encontrados: {count_horarios}")

            # Si no hay horarios, puede ser problema de tenant
            if count_horarios == 0:
                error_msg = "No hay horarios configurados."
                if not tenant_detected:
                    error_msg += " Además, no se detectó el tenant. Verifica la configuración de tu clínica."
                logger.error(f"[Horarios Disponibles] {error_msg}")
                return Response(
                    {"detail": error_msg, "tenant_detected": tenant_detected},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"[Horarios Disponibles] Error al obtener horarios del tenant: {str(e)}")
            return Response(
                {"detail": f"Error al consultar horarios: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 5. FILTRAR HORARIOS OCUPADOS
        try:
            horarios_ocupados_query = Consulta.objects.filter(
                cododontologo_id=odontologo_id,
                fecha=fecha_obj  # Usar objeto date en lugar de string
            )

            # Filtrar por tenant
            if tenant_detected:
                horarios_ocupados_query = horarios_ocupados_query.filter(empresa=request.tenant)

            horarios_ocupados = horarios_ocupados_query.values_list('idhorario_id', flat=True)
            logger.info(f"[Horarios Disponibles] Horarios ocupados IDs: {list(horarios_ocupados)}")
        except Exception as e:
            logger.error(f"[Horarios Disponibles] Error al filtrar horarios ocupados: {str(e)}")
            return Response(
                {"detail": f"Error al consultar horarios ocupados: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 6. CALCULAR HORARIOS DISPONIBLES
        try:
            horarios_disponibles = todos_horarios.exclude(id__in=horarios_ocupados)
            count_disponibles = horarios_disponibles.count()
            logger.info(f"[Horarios Disponibles] Horarios disponibles: {count_disponibles}")

            serializer = self.get_serializer(horarios_disponibles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[Horarios Disponibles] Error al serializar horarios: {str(e)}")
            return Response(
                {"detail": f"Error al procesar horarios disponibles: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipodeconsultaViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TipodeconsultaSerializer

    def get_queryset(self):
        """Filtra tipos de consulta por empresa (multi-tenancy)"""
        queryset = Tipodeconsulta.objects.all()

        # Filtrar por tenant si está disponible
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        return queryset


class EstadodeconsultaViewSet(ReadOnlyModelViewSet):
    """
    Catálogo de estados de consulta (ej: Agendada, Confirmada, Atendida, Cancelada).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EstadodeconsultaSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Estadodeconsulta.objects.all()
        if hasattr(self.request, 'tenant') and self.request.tenant:
            qs = qs.filter(empresa=self.request.tenant)
        return qs.order_by('estado')


# -------------------- ADMIN: Roles y Usuarios --------------------

class TipodeusuarioViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TipodeusuarioSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Tipodeusuario.objects.all().order_by("id")
        t = _tenant(self.request)
        if t:
            qs = qs.filter(Q(empresa=t) | Q(empresa__isnull=True))
        return qs


class UsuarioViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UsuarioAdminSerializer

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nombre", "apellido", "correoelectronico"]
    ordering = ["apellido", "nombre"]

    lookup_field = "codigo"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        """Filtra usuarios por empresa (multi-tenancy)"""
        queryset = Usuario.objects.select_related("idtipousuario")

        # Filtrar por tenant si está disponible
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        return queryset

    def partial_update(self, request, *args, **kwargs):
        # Solo administradores del tenant (o staff) pueden cambiar roles
        if not (_es_admin_por_tabla(request) or getattr(request.user, "is_staff", False)):
            return Response({"detail": "Solo administradores pueden cambiar roles."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='por-roles')
    def por_roles(self, request):
        # /api/usuarios/por-roles/?ids=1,3,4
        ids_param = request.query_params.get('ids', '')
        try:
            ids = [int(x) for x in ids_param.split(',') if x.strip()]
        except ValueError:
            return Response({"detail": "Parámetro 'ids' inválido"}, status=400)

        qs = self.get_queryset().filter(idtipousuario_id__in=ids).order_by('apellido', 'nombre')
        data = UsuarioAdminSerializer(qs, many=True).data
        return Response(data)


def ping(_):
    return JsonResponse({"ok": True})


# -------------------- Perfil de Usuario --------------------

class UserProfileView(RetrieveUpdateAPIView):
    """
    Vista para leer y actualizar los datos del perfil del usuario autenticado.
    Soporta GET, PUT y PATCH.
    """
    # serializer_class = UsuarioMeSerializer  # si deseas devolver/actualizar el perfil
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        En lugar de devolver request.user directamente, buscamos el perfil 'Usuario'
        que está vinculado a ese usuario de autenticación.
        """
        try:
            usuario_perfil = Usuario.objects.get(correoelectronico__iexact=self.request.user.email)
            return usuario_perfil
        except Usuario.DoesNotExist:
            return None


# -------------------- Historias Clínicas (HCE) --------------------

class HistorialclinicoViewSet(mixins.CreateModelMixin,
                              mixins.ListModelMixin,
                              GenericViewSet):
    """
    Endpoints:
      - POST /api/historias-clinicas/                (crear HCE; calcula episodio siguiente y valida duplicado por día+motivo)
      - GET  /api/historias-clinicas/?paciente=<id>  (listar HCE por paciente; ordenado por fecha/episodio)
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return (HistorialclinicoCreateSerializer
                if self.action == 'create'
                else HistorialclinicoListSerializer)

    def get_queryset(self):
        """Filtra historias clínicas por empresa (multi-tenancy)"""
        qs = Historialclinico.objects.select_related(
            'pacientecodigo', 'pacientecodigo__codusuario'
        )

        # Filtrar por tenant si está disponible
        if hasattr(self.request, 'tenant') and self.request.tenant:
            qs = qs.filter(empresa=self.request.tenant)

        # Filtro adicional por paciente específico
        pid = self.request.query_params.get('paciente')
        if pid:
            qs = qs.filter(pacientecodigo_id=pid)

        return qs.order_by('-fecha', '-episodio')

    def perform_create(self, serializer):
        """Asigna automáticamente la empresa del tenant al crear historia clínica"""
        if hasattr(self.request, 'tenant') and self.request.tenant:
            serializer.save(empresa=self.request.tenant)
        else:
            serializer.save()


# -------------------- Consentimiento Digital --------------------
from .utils_consentimiento import sellar_documento_consentimiento, calcular_hash_documento, \
    generar_pdf_consentimiento  # <-- centraliza imports


class ConsentimientoViewSet(ModelViewSet):
    """
    API para gestionar los Consentimientos Digitales.
    - `GET /api/consentimientos/`: Lista todos los consentimientos del tenant.
    - `GET /api/consentimientos/?paciente=<id>`: Filtra consentimientos por paciente.
    - `POST /api/consentimientos/`: Crea un nuevo consentimiento.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConsentimientoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['paciente']
    search_fields = ['paciente__codusuario__nombre', 'paciente__codusuario__apellido', 'titulo']

    def perform_create(self, serializer):
        """
        Asegura que el tenant esté configurado antes de crear el consentimiento
        y procesa automáticamente el sellado digital
        """
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            raise serializers.ValidationError({
                "error": "No se pudo determinar el tenant",
                "detail": "Se requiere un tenant válido para crear consentimientos"
            })

        print(f"[ConsentimientoViewSet] Creating consent with tenant: {self.request.tenant}")

        # Guardar el consentimiento inicialmente
        consentimiento = serializer.save(empresa=self.request.tenant)

        # Procesar el sellado digital automáticamente
        try:
            sellar_documento_consentimiento(consentimiento)
        except Exception as e:
            print(f"[ConsentimientoViewSet] Error al sellar documento: {e}")
            # Aún si hay error en el sellado, el consentimiento se guarda

    def get_queryset(self):
        """
        Filtra los consentimientos para que solo se muestren los que pertenecen
        a la empresa (tenant) actual.
        """
        queryset = Consentimiento.objects.select_related('paciente__codusuario', 'empresa')

        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)
        else:
            queryset = queryset.none()

        return queryset.order_by('-fecha_creacion')

    def get_serializer_context(self):
        """
        Inyecta el objeto 'request' en el contexto del serializador.
        Esto es crucial para que el serializador pueda acceder al tenant y a la IP.
        """
        return {'request': self.request}

    @action(detail=True, methods=['get'], url_path='pdf')
    def descargar_pdf(self, request, pk=None):
        """
        Descarga el PDF firmado del consentimiento
        """
        consentimiento = self.get_queryset().get(pk=pk)

        # Si ya tenemos un PDF almacenado, lo devolvemos directamente
        if consentimiento.pdf_firmado and len(consentimiento.pdf_firmado) > 0:
            response = HttpResponse(
                consentimiento.pdf_firmado,
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="consentimiento_{pk}.pdf"'
            return response

        # Si no hay PDF almacenado, generamos uno nuevo
        if not consentimiento.firma_base64:
            return Response(
                {"detail": "No se encontró la firma para este consentimiento"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Generar el PDF con la información actual
            pdf_generado = generar_pdf_consentimiento(consentimiento)

            # Actualizar el registro con el PDF generado
            consentimiento.pdf_firmado = pdf_generado
            if not consentimiento.hash_documento:
                consentimiento.hash_documento = calcular_hash_documento(pdf_generado)
            if not consentimiento.fecha_hora_sello:
                consentimiento.fecha_hora_sello = datetime.now()
            consentimiento.save(update_fields=['pdf_firmado', 'hash_documento', 'fecha_hora_sello'])

            response = HttpResponse(
                pdf_generado,
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="consentimiento_{pk}.pdf"'
            return response
        except Exception as e:
            print(f"Error al generar o devolver PDF: {e}")
            import traceback
            print(traceback.format_exc())
            return Response(
                {"detail": f"Error al generar el PDF del consentimiento: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='validar')
    def validar_consentimiento(self, request, pk=None):
        """
        Valida que el consentimiento no haya sido alterado
        """
        consentimiento = self.get_object()

        if not consentimiento.pdf_firmado or not consentimiento.hash_documento:
            return Response(
                {"detail": "No se puede validar este consentimiento"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Recalcular el hash del PDF almacenado
        hash_actual = calcular_hash_documento(bytes(consentimiento.pdf_firmado))

        # Comparar con el hash almacenado
        es_valido = hash_actual == consentimiento.hash_documento

        return Response({
            "valido": es_valido,
            "hash_almacenado": consentimiento.hash_documento,
            "hash_actual": hash_actual,
            "fecha_sello": consentimiento.fecha_hora_sello,
            "validado_por": f"{consentimiento.validado_por.nombre} {consentimiento.validado_por.apellido}" if consentimiento.validado_por else None,
            "fecha_validacion": consentimiento.fecha_validacion
        })

    @action(detail=True, methods=['post'], url_path='firmar-validar')
    def firmar_y_validar(self, request, pk=None):
        """
        Permite a un usuario autorizado validar un consentimiento
        """
        consentimiento = self.get_object()

        # Verificar que el usuario tenga permisos para validar
        if not hasattr(request.user, 'usuario') or request.user.usuario.idtipousuario.rol not in ['Administrador',
                                                                                                  'Odontólogo']:
            return Response(
                {"detail": "No tienes permisos para validar consentimientos"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Actualizar los datos de validación
        consentimiento.validado_por = request.user.usuario
        consentimiento.fecha_validacion = datetime.now()
        consentimiento.save()

        return Response({
            "detail": "Consentimiento validado exitosamente",
            "validado_por": f"{consentimiento.validado_por.nombre} {consentimiento.validado_por.apellido}",
            "fecha_validacion": consentimiento.fecha_validacion
        })


# -------------------- Bitácora de Auditoría --------------------

class BitacoraViewSet(ReadOnlyModelViewSet):
    """
    API read-only para la Bitácora de auditoría.
    Solo usuarios admin pueden ver los registros.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BitacoraSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['descripcion', 'usuario__nombre', 'usuario__apellido', 'ip_address']
    ordering_fields = ['fecha_hora', 'accion', 'usuario__nombre']
    ordering = ['-fecha_hora']  # Más recientes primero

    def get_queryset(self):
        # Solo admins pueden ver la bitácora
        if not _es_admin_por_tabla(self.request):
            return Bitacora.objects.none()

        queryset = Bitacora.objects.select_related('usuario')

        # Filtrar por tenant si está disponible (multi-tenancy)
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        # Filtros opcionales por parámetros GET
        accion = self.request.query_params.get('accion', None)
        if accion:
            queryset = queryset.filter(accion=accion)

        usuario_id = self.request.query_params.get('usuario_id', None)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        # Filtro por fechas
        fecha_desde = self.request.query_params.get('fecha_desde', None)
        fecha_hasta = self.request.query_params.get('fecha_hasta', None)

        if fecha_desde:
            try:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
                fecha_desde = make_aware(fecha_desde)
                queryset = queryset.filter(fecha_hora__gte=fecha_desde)
            except ValueError:
                pass

        if fecha_hasta:
            try:
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                fecha_hasta = make_aware(fecha_hasta.replace(hour=23, minute=59, second=59))
                queryset = queryset.filter(fecha_hora__lte=fecha_hasta)
            except ValueError:
                pass

        return queryset

    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        Endpoint para obtener estadísticas de la bitácora
        """
        if not _es_admin_por_tabla(request):
            return Response(
                {"detail": "No tienes permisos para ver las estadísticas."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Estadísticas de los últimos 30 días
        fecha_limite = make_aware(datetime.now() - timedelta(days=30))
        queryset = Bitacora.objects.filter(fecha_hora__gte=fecha_limite)

        # Contar por acción
        acciones = {}
        for registro in queryset:
            accion = registro.get_accion_display()
            acciones[accion] = acciones.get(accion, 0) + 1

        # Usuarios más activos
        usuarios_activos = {}
        for registro in queryset.filter(usuario__isnull=False).select_related('usuario'):
            nombre = f"{registro.usuario.nombre} {registro.usuario.apellido}"
            usuarios_activos[nombre] = usuarios_activos.get(nombre, 0) + 1

        # Ordenar usuarios por actividad
        usuarios_activos = dict(sorted(usuarios_activos.items(), key=lambda x: x[1], reverse=True)[:10])

        # Actividad por día (últimos 7 días)
        actividad_diaria = {}
        for i in range(7):
            fecha = datetime.now() - timedelta(days=i)
            fecha_str = fecha.strftime('%d/%m')
            inicio_dia = make_aware(fecha.replace(hour=0, minute=0, second=0, microsecond=0))
            fin_dia = make_aware(fecha.replace(hour=23, minute=59, second=59, microsecond=999999))

            count = queryset.filter(fecha_hora__range=[inicio_dia, fin_dia]).count()
            actividad_diaria[fecha_str] = count

        return Response({
            'total_registros': queryset.count(),
            'acciones': acciones,
            'usuarios_activos': usuarios_activos,
            'actividad_diaria': actividad_diaria,
            'periodo': 'Últimos 30 días'
        })

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        """
        Endpoint para exportar bitácora en CSV o PDF
        """
        if not _es_admin_por_tabla(request):
            return Response(
                {"detail": "No tienes permisos para exportar la bitácora."},
                status=status.HTTP_403_FORBIDDEN
            )

        format_type = request.query_params.get('format', 'csv').lower()

        # Obtener datos con filtros aplicados
        queryset = self.get_queryset()

        # Aplicar filtros de la query
        accion = request.query_params.get('accion', None)
        if accion:
            queryset = queryset.filter(accion=accion)

        fecha_desde = request.query_params.get('fecha_desde', None)
        fecha_hasta = request.query_params.get('fecha_hasta', None)

        if fecha_desde:
            try:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
                fecha_desde = make_aware(fecha_desde)
                queryset = queryset.filter(fecha_hora__gte=fecha_desde)
            except ValueError:
                pass

        if fecha_hasta:
            try:
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                fecha_hasta = make_aware(fecha_hasta.replace(hour=23, minute=59, second=59))
                queryset = queryset.filter(fecha_hora__lte=fecha_hasta)
            except ValueError:
                pass

        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(descripcion__icontains=search) |
                Q(usuario__nombre__icontains=search) |
                Q(usuario__apellido__icontains=search) |
                Q(ip_address__icontains=search)
            )

        if format_type == 'csv':
            return self._export_csv(queryset)
        elif format_type == 'pdf':
            return self._export_pdf(queryset)
        else:
            return Response({"detail": "Formato no soportado"}, status=status.HTTP_400_BAD_REQUEST)

    def _export_csv(self, queryset):
        """Exportar a CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="bitacora_{datetime.now().strftime("%Y%m%d")}.csv"'

        # Agregar BOM para Excel
        response.write('\ufeff')

        writer = csv.writer(response)

        # Escribir headers
        writer.writerow([
            'Fecha/Hora',
            'Acción',
            'Usuario',
            'Descripción',
            'IP',
            'Navegador',
            'Modelo Afectado',
            'Objeto ID'
        ])

        # Escribir datos
        for entry in queryset[:1000]:  # Limitar a 1000 registros
            usuario_nombre = f"{entry.usuario.nombre} {entry.usuario.apellido}" if entry.usuario else "Usuario anónimo"

            writer.writerow([
                entry.fecha_hora.strftime('%d/%m/%Y %H:%M:%S'),
                entry.get_accion_display(),
                usuario_nombre,
                entry.descripcion or '',
                entry.ip_address,
                entry.user_agent or '',
                entry.modelo_afectado or '',
                entry.objeto_id or ''
            ])

        return response

    def _export_pdf(self, queryset):
        """Exportar a PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            return Response(
                {"detail": "PDF export no disponible. Instale reportlab: pip install reportlab"},
                status=status.HTTP_400_BAD_REQUEST
            )

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centrado
        )

        # Título
        title = Paragraph("Bitácora de Auditoría", title_style)
        elements.append(title)

        # Fecha de generación
        fecha_gen = Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
        elements.append(fecha_gen)
        elements.append(Spacer(1, 20))

        # Datos de la tabla
        data = [['Fecha/Hora', 'Acción', 'Usuario', 'Descripción', 'IP']]

        for entry in queryset[:100]:  # Limitar a 100 para PDF
            usuario_nombre = f"{entry.usuario.nombre} {entry.usuario.apellido}" if entry.usuario else "Anónimo"

            data.append([
                entry.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                entry.get_accion_display(),
                usuario_nombre,
                (entry.descripcion or '')[:50] + '...' if len(entry.descripcion or '') > 50 else (
                        entry.descripcion or ''),
                entry.ip_address
            ])

        # Crear tabla
        table = Table(data, colWidths=[1.2 * inch, 1 * inch, 1.2 * inch, 2 * inch, 1 * inch])

        # Estilo de tabla
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="bitacora_{datetime.now().strftime("%Y%m%d")}.pdf"'

        return response


# ============================================================================
# DOCUMENTOS CLÍNICOS - S3
# ============================================================================
import boto3
from botocore.exceptions import ClientError
import os


class DocumentoClinicoViewSet(ModelViewSet):
    """
    ViewSet para gestionar documentos clínicos almacenados en S3.
    Permite subir, listar, descargar y eliminar documentos vinculados a pacientes.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['nombre_archivo', 'tipo_documento', 'notas']
    ordering_fields = ['fecha_creacion', 'fecha_documento', 'tipo_documento']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        from .models import DocumentoClinico
        queryset = DocumentoClinico.objects.select_related(
            'codpaciente',
            'codpaciente__codusuario',
            'profesional_carga'
        )

        # Filtrar por tenant si está disponible (multi-tenancy)
        if hasattr(self.request, 'tenant') and self.request.tenant:
            queryset = queryset.filter(empresa=self.request.tenant)

        # Filtro por paciente
        codpaciente = self.request.query_params.get('codpaciente')
        if codpaciente:
            queryset = queryset.filter(codpaciente__codusuario=codpaciente)

        # Filtro por tipo de documento
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_documento=tipo)

        # Filtro por consulta
        idconsulta = self.request.query_params.get('idconsulta')
        if idconsulta:
            queryset = queryset.filter(idconsulta=idconsulta)

        # Filtro por historial clínico
        idhistorialclinico = self.request.query_params.get('idhistorialclinico')
        if idhistorialclinico:
            queryset = queryset.filter(idhistorialclinico=idhistorialclinico)

        return queryset

    def get_serializer_class(self):
        from .serializers import DocumentoClinicoSerializer, DocumentoClinicoUploadSerializer
        if self.action == 'upload':
            return DocumentoClinicoUploadSerializer
        return DocumentoClinicoSerializer

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Endpoint para subir documentos clínicos a S3.
        POST /api/documentos-clinicos/upload/
        """
        from .serializers import DocumentoClinicoUploadSerializer, DocumentoClinicoSerializer
        from .models import DocumentoClinico, Paciente

        serializer = DocumentoClinicoUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        archivo = serializer.validated_data['archivo']
        codpaciente = serializer.validated_data['codpaciente']

        # Generar nombre único para S3
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        extension = os.path.splitext(archivo.name)[1]
        nombre_s3 = f"documentos_clinicos/{codpaciente}/{timestamp}_{archivo.name}"

        try:
            # Configurar cliente S3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            # Subir archivo a S3
            s3_client.upload_fileobj(
                archivo.file,
                settings.AWS_STORAGE_BUCKET_NAME,
                nombre_s3,
                ExtraArgs={
                    'ContentType': archivo.content_type
                    # ACL removido - se maneja con políticas del bucket
                }
            )

            # Generar URL del archivo
            url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{nombre_s3}"

            # Buscar el Usuario (modelo de negocio) del usuario autenticado
            usuario_profesional = None
            if request.user.is_authenticated:
                try:
                    usuario_profesional = Usuario.objects.get(
                        correoelectronico__iexact=request.user.email
                    )
                except Usuario.DoesNotExist:
                    pass

            # Crear registro en la base de datos
            documento = DocumentoClinico.objects.create(
                codpaciente_id=codpaciente,
                idconsulta_id=serializer.validated_data.get('idconsulta'),
                idhistorialclinico_id=serializer.validated_data.get('idhistorialclinico'),
                tipo_documento=serializer.validated_data['tipo_documento'],
                nombre_archivo=archivo.name,
                url_s3=url_s3,
                s3_key=nombre_s3,
                tamanio_bytes=archivo.size,
                extension=extension.lstrip('.'),
                profesional_carga=usuario_profesional,
                fecha_documento=serializer.validated_data['fecha_documento'],
                notas=serializer.validated_data.get('notas', ''),
                empresa=getattr(request, 'tenant', None)
            )

            # Registrar en bitácora
            self._crear_bitacora(
                request,
                'SUBIDA_DOCUMENTO',
                f"Documento '{archivo.name}' subido para paciente ID {codpaciente}",
                'DocumentoClinico',
                str(documento.id)
            )

            return Response(
                DocumentoClinicoSerializer(documento).data,
                status=status.HTTP_201_CREATED
            )

        except ClientError as e:
            return Response(
                {'error': f'Error al subir archivo a S3: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Error inesperado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download_url(self, request, pk=None):
        """
        Endpoint para generar URL de descarga firmada (válida 1 hora).
        GET /api/documentos-clinicos/{id}/download_url/
        """
        documento = self.get_object()

        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            # Generar URL firmada válida por 1 hora
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': documento.s3_key
                },
                ExpiresIn=3600  # 1 hora
            )

            # Registrar acceso en bitácora
            self._crear_bitacora(
                request,
                'DESCARGA_DOCUMENTO',
                f"Generada URL de descarga para documento '{documento.nombre_archivo}'",
                'DocumentoClinico',
                str(documento.id)
            )

            return Response({'download_url': url})

        except ClientError as e:
            return Response(
                {'error': f'Error al generar URL de descarga: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar documento (tanto de S3 como de BD).
        DELETE /api/documentos-clinicos/{id}/
        """
        documento = self.get_object()

        try:
            # Eliminar de S3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            s3_client.delete_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=documento.s3_key
            )

            # Registrar en bitácora antes de eliminar
            self._crear_bitacora(
                request,
                'ELIMINACION_DOCUMENTO',
                f"Documento '{documento.nombre_archivo}' eliminado",
                'DocumentoClinico',
                str(documento.id)
            )

            # Eliminar de BD
            documento.delete()

            return Response(
                {'message': 'Documento eliminado correctamente'},
                status=status.HTTP_204_NO_CONTENT
            )

        except ClientError as e:
            return Response(
                {'error': f'Error al eliminar archivo de S3: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, *args, **kwargs):
        """
        Actualizar metadatos de un documento (PATCH).
        PATCH /api/documentos-clinicos/{id}/

        Permite modificar:
        - tipo_documento
        - fecha_documento
        - notas
        - idconsulta
        - idhistorialclinico

        NO permite modificar el archivo físico en S3.
        """
        documento = self.get_object()

        # Obtener datos antiguos para bitácora
        valores_anteriores = {
            'tipo_documento': documento.tipo_documento,
            'fecha_documento': str(documento.fecha_documento),
            'notas': documento.notas,
            'idconsulta': documento.idconsulta_id,
            'idhistorialclinico': documento.idhistorialclinico_id
        }

        # Actualizar campos simples
        if 'tipo_documento' in request.data:
            documento.tipo_documento = request.data['tipo_documento']

        if 'fecha_documento' in request.data:
            documento.fecha_documento = request.data['fecha_documento']

        if 'notas' in request.data:
            documento.notas = request.data['notas']

        # Actualizar Foreign Keys (usar _id para asignación directa)
        if 'idconsulta' in request.data:
            consulta_id = request.data['idconsulta']
            if consulta_id:
                # Validar que pertenezca al mismo paciente
                if not Consulta.objects.filter(
                        id=consulta_id,
                        codpaciente=documento.codpaciente
                ).exists():
                    return Response(
                        {'error': 'La consulta no pertenece al paciente del documento'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            documento.idconsulta_id = consulta_id  # ← CORREGIDO: usar _id

        if 'idhistorialclinico' in request.data:
            historial_id = request.data['idhistorialclinico']
            if historial_id:
                # Validar que pertenezca al mismo paciente
                if not Historialclinico.objects.filter(
                        id=historial_id,
                        pacientecodigo=documento.codpaciente
                ).exists():
                    return Response(
                        {'error': 'El historial clínico no pertenece al paciente del documento'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            documento.idhistorialclinico_id = historial_id  # ← CORREGIDO: usar _id

        documento.save()

        # Registrar en bitácora
        valores_nuevos = {
            'tipo_documento': documento.tipo_documento,
            'fecha_documento': str(documento.fecha_documento),
            'notas': documento.notas,
            'idconsulta': documento.idconsulta_id,
            'idhistorialclinico': documento.idhistorialclinico_id
        }

        self._crear_bitacora(
            request,
            'MODIFICACION_DOCUMENTO',
            f"Metadatos de documento '{documento.nombre_archivo}' actualizados",
            'DocumentoClinico',
            str(documento.id)
        )

        from .serializers import DocumentoClinicoSerializer
        return Response(
            DocumentoClinicoSerializer(documento).data,
            status=status.HTTP_200_OK
        )

    def _crear_bitacora(self, request, accion, descripcion, modelo, objeto_id):
        """Método auxiliar para crear registros en la bitácora"""
        try:
            Bitacora.objects.create(
                accion=accion,
                tabla_afectada=modelo,
                registro_id=objeto_id,
                usuario=request.user,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                empresa=getattr(request, 'tenant', None)
            )
        except Exception:
            pass  # No fallar si hay error en bitácora

    def _get_client_ip(self, request):
        """Obtener IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip