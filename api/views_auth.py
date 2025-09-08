# api/views_auth.py
from typing import Optional

from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError, DatabaseError

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers_auth import RegisterSerializer
from .models import Usuario, Paciente, Odontologo, Recepcionista

User = get_user_model()


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_token(request):
    """Siembra cookie CSRF (csrftoken). Útil si luego usas endpoints con sesión/CSRF."""
    return Response({"detail": "CSRF cookie set"})


def _resolve_tipodeusuario(idtipousuario: Optional[int]) -> int:
    """Compatibilidad legacy si llegara vacío (default paciente=2)."""
    return idtipousuario if idtipousuario else 2


@api_view(["POST"])
@authentication_classes([])      # público
@permission_classes([AllowAny])
def auth_register(request):
    """
    Registro (NO inicia sesión):
      1) Crea Django User (username=email).
      2) Crea/actualiza fila en 'usuario' (idtipousuario según rol).
      3) Crea subtipo 1-1 según 'rol' (default: paciente).
    """
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    email = data["email"].lower().strip()
    password = data["password"]
    nombre = (data.get("nombre") or "").strip()
    apellido = (data.get("apellido") or "").strip()
    telefono = (data.get("telefono") or "").strip() or None
    sexo = (data.get("sexo") or "").strip() or None

    rol_subtipo = (data.get("rol") or "paciente").strip().lower()
    idtu = data.get("idtipousuario") or _resolve_tipodeusuario(None)

    carnetidentidad = (data.get("carnetidentidad") or "").strip().upper()
    fechanacimiento = data.get("fechanacimiento")
    direccion = (data.get("direccion") or "").strip()

    try:
        with transaction.atomic():
            # 1) auth_user: email único
            try:
                dj_user = User.objects.create_user(username=email, email=email, password=password)
            except IntegrityError:
                return Response({"detail": "Ya existe un usuario con ese email."}, status=status.HTTP_409_CONFLICT)

            # Nombres (hasta 150 chars en Django moderno)
            update_fields = []
            if nombre:
                dj_user.first_name = nombre[:150]; update_fields.append("first_name")
            if apellido:
                dj_user.last_name = apellido[:150]; update_fields.append("last_name")
            if update_fields:
                dj_user.save(update_fields=update_fields)

            # 2) 'usuario' (dominio)
            usuario, created = Usuario.objects.get_or_create(
                correoelectronico=email,
                defaults={
                    "nombre": nombre or email.split("@")[0],
                    "apellido": apellido or "",
                    "telefono": telefono,
                    "sexo": sexo,
                    "idtipousuario_id": idtu,
                },
            )
            if not created:
                changed = False
                if usuario.idtipousuario_id != idtu:
                    usuario.idtipousuario_id = idtu; changed = True
                if nombre and usuario.nombre != nombre:
                    usuario.nombre = nombre; changed = True
                if apellido and usuario.apellido != apellido:
                    usuario.apellido = apellido; changed = True
                if telefono is not None and usuario.telefono != telefono:
                    usuario.telefono = telefono; changed = True
                if sexo is not None and usuario.sexo != sexo:
                    usuario.sexo = sexo; changed = True
                if changed:
                    usuario.save()

            # 3) Subtipo 1-1
            if rol_subtipo == "paciente":
                try:
                    Paciente.objects.update_or_create(
                        codusuario=usuario,
                        defaults={
                            "carnetidentidad": carnetidentidad,
                            "fechanacimiento": fechanacimiento,
                            "direccion": direccion,
                        },
                    )
                except IntegrityError:
                    # UNIQUE(carnetidentidad) en BD
                    return Response({"carnetidentidad": "El carnet ya existe."}, status=status.HTTP_409_CONFLICT)
            elif rol_subtipo == "odontologo":
                Odontologo.objects.get_or_create(codusuario=usuario)
            elif rol_subtipo == "recepcionista":
                Recepcionista.objects.get_or_create(codusuario=usuario)
            elif rol_subtipo == "administrador":
                # Administrador no tiene subtipo 1-1 en tu esquema actual
                pass
            else:
                # Fallback legacy -> paciente vacío
                Paciente.objects.get_or_create(codusuario=usuario)

    except DatabaseError as e:
        return Response({"detail": "Error al registrar.", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Respuesta compatible con tu FE
    return Response(
        {
            "ok": True,
            "message": "Usuario registrado.",
            "user": {
                "id": dj_user.id,
                "email": email,
                "first_name": dj_user.first_name,
                "last_name": dj_user.last_name,
            },
            "usuario_codigo": usuario.codigo,
            "subtipo": rol_subtipo,
            "idtipousuario": idtu,
        },
        status=status.HTTP_201_CREATED,
    )