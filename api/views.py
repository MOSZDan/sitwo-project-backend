from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import Paciente, Consulta, Odontologo, Horario, Tipodeconsulta
# Asegúrate de importar también los nuevos serializers que crearemos
from .serializers import PacienteSerializer, ConsultaSerializer, CreateConsultaSerializer, OdontologoMiniSerializer, \
    HorarioSerializer, TipodeconsultaSerializer, UpdateConsultaSerializer

from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend


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
    """Cuenta de usuarios del auth de Django (tabla auth_user)."""
    User = get_user_model()
    return JsonResponse({"users": User.objects.count()})


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
        if self.action in ['create', 'update', 'partial_update']:
            return CreateConsultaSerializer
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
    queryset = Odontologo.objects.all()
    serializer_class = OdontologoMiniSerializer


class HorarioViewSet(ReadOnlyModelViewSet):
    """Devuelve una lista de horarios disponibles."""
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer


class TipodeconsultaViewSet(ReadOnlyModelViewSet):
    """Devuelve los tipos de consulta."""
    queryset = Tipodeconsulta.objects.all()
    serializer_class = TipodeconsultaSerializer

    class ConsultaViewSet(ModelViewSet):
        # ... (queryset, filter_backends, etc. se quedan igual)

        def get_serializer_class(self):
            # 👇 MODIFICA ESTA FUNCIÓN
            if self.action == 'create':
                return CreateConsultaSerializer
            if self.action == 'partial_update':  # Cuando se usa PATCH
                return UpdateConsultaSerializer  # Usamos el nuevo serializador
            return ConsultaSerializer  # Para todo lo demás (GET)
