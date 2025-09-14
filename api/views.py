from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings

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


# -------------------- Consultas (Citas) --------------------

class ConsultaViewSet(ModelViewSet):
    """
    API para Consultas. Permite crear, leer, actualizar y eliminar.
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
                # Opcional: registrar el error si el correo no se pudo enviar
                print(f"Error al enviar correo de notificación: {e}")


# -------------------- Catálogos de soporte --------------------

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

    # --- Helpers de autorización ---

    def _es_admin_actual(self, dj_user) -> bool:
        """
        Considera admin si:
        - Es staff en Django, o
        - Su fila en 'usuario' (por email/username) tiene rol Administrador (id=1).
        """
        if getattr(dj_user, "is_staff", False):
            return True

        email = (getattr(dj_user, "email", None) or getattr(dj_user, "username", "")).strip().lower()
        if not email:
            return False

        dom = Usuario.objects.filter(correoelectronico__iexact=email).only("idtipousuario_id").first()
        return bool(dom and dom.idtipousuario_id == 1)  # 1 = Administrador (ajusta si tu ID difiere)

    def partial_update(self, request, *args, **kwargs):
        """
        Autorización: solo administradores pueden cambiar roles.
        Además, sincroniza is_staff en el auth_user del usuario modificado según su nuevo rol.
        """
        if not self._es_admin_actual(request.user):
            return Response({"detail": "Solo administradores pueden cambiar roles."}, status=403)

        # Ejecuta la actualización normal (cambia idtipousuario del Usuario de negocio)
        resp = super().partial_update(request, *args, **kwargs)

        # Sincroniza is_staff en el auth_user asociado al Usuario que acabas de modificar
        try:
            instance = self.get_object()  # Usuario (dominio) editado
            User = get_user_model()
            auth = (User.objects.filter(username__iexact=instance.correoelectronico).first()
                    or User.objects.filter(email__iexact=instance.correoelectronico).first())
            if auth:
                new_staff = (instance.idtipousuario_id == 1)  # 1 = Administrador
                if auth.is_staff != new_staff:
                    auth.is_staff = new_staff
                    auth.save(update_fields=["is_staff"])
        except Exception as e:
            # log opcional para diagnóstico
            print("sync is_staff error:", e)

        return resp

