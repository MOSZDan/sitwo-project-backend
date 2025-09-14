# api/views.py
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rest_framework.viewsets import ModelViewSet
from django.core.mail import send_mail
from django.conf import settings

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import ( Paciente, Consulta, Odontologo, Horario, Tipodeconsulta,
Usuario, Tipodeusuario, Vista )
# Asegúrate de importar también los nuevos serializers que crearemos
from .serializers import PacienteSerializer, ConsultaSerializer, CreateConsultaSerializer, OdontologoMiniSerializer, \
    HorarioSerializer, TipodeconsultaSerializer

from .serializers import (
    PacienteSerializer,
    ConsultaSerializer,
    CreateConsultaSerializer,
    OdontologoMiniSerializer,
    HorarioSerializer,
    TipodeconsultaSerializer,
    UpdateConsultaSerializer,
    # Admin
    UsuarioAdminSerializer,
    TipodeusuarioSerializer,
    VistaSerializer,  # ← NUEVO
)

# -------------------- Health / Utils --------------------

@csrf_exempt
@require_http_methods(["GET"])
def health(request):
    """Ping de salud"""
    return JsonResponse({"ok": True})

@csrf_exempt
@require_http_methods(["GET"])
def db_info(request):
    """Info rápida de la conexión a DB"""
    with connection.cursor() as cur:
        cur.execute("select current_database(), current_user")
        db, user = cur.fetchone()
    return JsonResponse({"database": db, "user": user})

@csrf_exempt
@require_http_methods(["GET"])
def users_count(request):
    """Cuenta de usuarios del auth de Django"""
    User = get_user_model()
    return JsonResponse({"count": User.objects.count()})


# Helper reutilizable: ¿el usuario actual es admin en la tabla de negocio?
def _es_admin_por_tabla(dj_user) -> bool:
    email = (getattr(dj_user, "email", None) or getattr(dj_user, "username", "")).strip().lower()
    if not email:
        return False
    return Usuario.objects.filter(
        correoelectronico__iexact=email,
        idtipousuario_id=1  # 1 = Administrador
    ).exists()


# -------------------- Pacientes --------------------

class PacienteViewSet(ReadOnlyModelViewSet):
    """
    API read-only de Pacientes.
    Requiere sesión activa (IsAuthenticated) y trae el Usuario relacionado.
    """
    permission_classes = [IsAuthenticated]
    queryset = Paciente.objects.select_related("codusuario").all()
    serializer_class = PacienteSerializer


class ConsultaViewSet(ModelViewSet):  # 👈 ¡CAMBIO IMPORTANTE!
    """
    API para Consultas. Ahora permite crear, leer, actualizar y eliminar.
    """
    permission_classes = [IsAuthenticated]
    queryset = (
        Consulta.objects.select_related(
            "codpaciente__codusuario",
            "cododontologo__codusuario",
            "codrecepcionista__codusuario",
            "idhorario",
            "idtipoconsulta",
            "idestadoconsulta",
        ).all()
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['codpaciente', 'fecha']

    def get_serializer_class(self):
        if self.action in ["create", "update"]:
            return CreateConsultaSerializer
        if self.action == "partial_update":
            return UpdateConsultaSerializer
        return ConsultaSerializer

   def perform_create(self, serializer):
        consulta = serializer.save()

        paciente = consulta.codpaciente
        usuario_paciente = paciente.codusuario

        if getattr(usuario_paciente, "recibir_notificaciones", False):
            try:
                subject = "Confirmación de tu cita en Clínica Dental"
                message = (
                    f"Hola {usuario_paciente.nombre}, tu cita para el día "
                    f"{consulta.fecha.strftime('%d/%m/%Y')} a las "
                    f"{consulta.idhorario.hora.strftime('%H:%M')} ha sido confirmada."
                )
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [usuario_paciente.correoelectronico]
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception as e:
                print(f"Error al enviar correo de notificación: {e}")
class OdontologoViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Odontologo.objects.all()
    serializer_class = OdontologoMiniSerializer


class HorarioViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer


class TipodeconsultaViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Tipodeconsulta.objects.all()
    serializer_class = TipodeconsultaSerializer


# -------------------- ADMIN: Roles y Usuarios --------------------

class TipodeusuarioViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Tipodeusuario.objects.all().order_by("id")
    serializer_class = TipodeusuarioSerializer
    pagination_class = None


class UsuarioViewSet(ModelViewSet):
    """
    Lista/búsqueda de usuarios y permite cambiar el rol (idtipousuario) vía PATCH.
    Cualquier usuario que sea Administrador en la tabla (idtipousuario_id == 1)
    puede cambiar roles (no depende de is_staff).
    """
    permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.select_related("idtipousuario").all()
    serializer_class = UsuarioAdminSerializer

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nombre", "apellido", "correoelectronico"]
    ordering = ["apellido", "nombre"]

    lookup_field = "codigo"
    http_method_names = ["get", "patch", "head", "options"]

    def partial_update(self, request, *args, **kwargs):
        """
        Autorización: solo administradores pueden cambiar roles.
        Admin = user.is_staff OR Usuario.idtipousuario_id == 1 (buscando por email/username).
        """
        user = request.user
        is_staff = getattr(user, "is_staff", False)
        es_admin_tabla = _es_admin_por_tabla(user)

        if not (is_staff or es_admin_tabla):
            return Response({"detail": "Solo administradores pueden cambiar roles."}, status=403)

        return super().partial_update(request, *args, **kwargs)


# -------------------- NUEVO: Gestionar Permisos (Vistas) --------------------

class VistaViewSet(ModelViewSet):
    """
    Administra las vistas (páginas) y los roles que pueden acceder.
    - GET list/retrieve: autenticado
    - POST/PATCH/DELETE: solo administradores (tabla o is_staff)
    - mis-vistas: vistas permitidas al usuario logueado (por su rol)
    """
    permission_classes = [IsAuthenticated]
    queryset = Vista.objects.prefetch_related("roles_permitidos").all()
    serializer_class = VistaSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        if not (getattr(request.user, "is_staff", False) or _es_admin_por_tabla(request.user)):
            return Response({"detail": "Solo administradores."}, status=403)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not (getattr(request.user, "is_staff", False) or _es_admin_por_tabla(request.user)):
            return Response({"detail": "Solo administradores."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (getattr(request.user, "is_staff", False) or _es_admin_por_tabla(request.user)):
            return Response({"detail": "Solo administradores."}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="mis-vistas")
    def mis_vistas(self, request):
        dom = getattr(request.user, "usuario", None)
        rol_id = getattr(dom, "idtipousuario_id", None)
        if not rol_id:
            return Response([], status=200)
        vistas = self.get_queryset().filter(roles_permitidos__id=rol_id)
        data = VistaSerializer(vistas, many=True).data
        return Response(data, status=200)
