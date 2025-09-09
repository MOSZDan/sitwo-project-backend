from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import viewsets

from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import Paciente, Consulta
from .serializers import PacienteSerializer, ConsultaSerializer, CreateConsultaSerializer


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


class ConsultaViewSet(viewsets.ModelViewSet):
    """
    API para leer, crear, actualizar y eliminar Consultas (citas).
    Requiere sesión activa (IsAuthenticated).
    Usa un serializer diferente para la creación vs. la lectura.
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

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateConsultaSerializer
        return ConsultaSerializer
