from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.viewsets import ModelViewSet

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Paciente, Consulta, Odontologo, Horario, Tipodeconsulta,
    Usuario, Tipodeusuario,
)

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
)

# -------------------- Health / Utils --------------------

def health(request):
    """Ping de salud"""
    return JsonResponse({"ok": True})


def db_info(request):
    """Info rápida de la conexión a DB (útil en dev/diagnóstico)."""
    with connection.cursor() as cur:
        cur.execute("select current_database(), current_user")
        db, user = cur.fetchone()
    return JsonResponse({"database": db, "user": user})


def users_count(request):
    """
    Cuenta de usuarios del auth de Django (tabla auth_user).
    NOTA: devolvemos 'count' para cuadrar con el frontend.
    """
    User = get_user_model()
    return JsonResponse({"count": User.objects.count()})


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

    # Esto permite usar un serializer para leer y otro para crear/actualizar
    def get_serializer_class(self):
        # Crear y actualizar completa usan el payload de creación
        if self.action in ["create", "update"]:
            return CreateConsultaSerializer
        # PATCH (actualización parcial)
        if self.action == "partial_update":
            return UpdateConsultaSerializer
        # GET / list / retrieve
        return ConsultaSerializer

    def perform_create(self, serializer):
        # Primero, guarda la nueva consulta
        consulta = serializer.save()

        # Ahora, envía la notificación por correo si el paciente lo permite
        paciente = consulta.codpaciente
        usuario_paciente = paciente.codusuario

        if usuario_paciente.recibir_notificaciones:
            try:
                # Asunto y mensaje del correo
                subject = "Confirmación de tu cita en Clínica Dental"
                message = f"Hola {usuario_paciente.nombre}, tu cita para el día {consulta.fecha.strftime('%d/%m/%Y')} a las {consulta.idhorario.hora.strftime('%H:%M')} ha sido confirmada."
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [usuario_paciente.correoelectronico]

                # Envía el correo
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)

            except Exception as e:
                # Opcional: registrar el error si el correo no se pudo enviar
                print(f"Error al enviar correo de notificación: {e}")


class OdontologoViewSet(ReadOnlyModelViewSet):
    """Devuelve una lista de odontólogos."""
    permission_classes = [IsAuthenticated]
    queryset = Odontologo.objects.all()
    serializer_class = OdontologoMiniSerializer


class HorarioViewSet(ReadOnlyModelViewSet):
    """Devuelve una lista de horarios disponibles."""
    permission_classes = [IsAuthenticated]
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer


class TipodeconsultaViewSet(ReadOnlyModelViewSet):
    """Devuelve los tipos de consulta."""
    permission_classes = [IsAuthenticated]
    queryset = Tipodeconsulta.objects.all()
    serializer_class = TipodeconsultaSerializer


# -------------------- ADMIN: Roles y Usuarios --------------------

class TipodeusuarioViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Tipodeusuario.objects.all().order_by("id")  # ← antes decía "identificacion"
    serializer_class = TipodeusuarioSerializer
    pagination_class = None



class UsuarioViewSet(ModelViewSet):
    """
    Lista/búsqueda de usuarios y permite cambiar el rol (idtipousuario) vía PATCH.
    Lectura para autenticados; cambio de rol restringido a administradores.
    """
    permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.select_related("idtipousuario").all()
    serializer_class = UsuarioAdminSerializer

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nombre", "apellido", "correoelectronico"]
    ordering = ["apellido", "nombre"]

    # Usamos el campo 'codigo' como identificador público en las rutas
    lookup_field = "codigo"

    # Solo GET y PATCH (no creamos/ borramos usuarios desde aquí)
    http_method_names = ["get", "patch", "head", "options"]

    def partial_update(self, request, *args, **kwargs):
        """
        Chequeo inline: solo administradores pueden cambiar roles.
        Admin = user.is_staff o usuario.idtipousuario_id == 1
        """
        user = request.user
        is_staff = getattr(user, "is_staff", False)
        dom = getattr(user, "usuario", None)
        is_admin = getattr(dom, "idtipousuario_id", None) == 1  # 1 = Administrador

        if not (is_staff or is_admin):
            return Response({"detail": "Solo administradores pueden cambiar roles."}, status=403)

        return super().partial_update(request, *args, **kwargs)
