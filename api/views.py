from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import connection

from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import Paciente, Consulta
from .serializers import PacienteSerializer, ConsultaSerializer


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


class ConsultaViewSet(ReadOnlyModelViewSet):
    """
    API read-only de Consultas.
    Requiere sesión activa (IsAuthenticated) y hace select_related de sus relaciones
    para evitar N+1 queries.
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
    serializer_class = ConsultaSerializer
