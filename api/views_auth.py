# api/views_auth.py
from typing import Optional

from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import get_user_model, login
from django.db import transaction, IntegrityError

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
    """Siembra cookie CSRF (csrftoken). Llamar antes de POST/PUT/PATCH/DELETE."""
    return Response({"detail": "CSRF cookie set"})


def _resolve_tipodeusuario(idtipousuario: Optional[int]) -> int:
    """
    Si el body trae idtipousuario, úsalo.
    Si NO trae, usa 2 por defecto (catálogo: Paciente).
    """
    return idtipousuario if idtipousuario else 2


@api_view(["POST"])
@authentication_classes([])      # público
@permission_classes([AllowAny])
def auth_register(request):
    """
    Registro:
      1) Crea Django User (email como username).
      2) Crea/actualiza fila en 'usuario' (idtipousuario=2 por defecto si no envían).
      3) Crea subtipo 1-1 según 'rol' (default: paciente) y guarda datos de paciente.
      4) Inicia sesión automáticamente (deja cookie 'sessionid').
    Body JSON:
      {
        email, password, nombre?, apellido?, telefono?, sexo?, idtipousuario?, rol?,
        carnetidentidad?, fechanacimiento?, direccion?
      }
    """
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    email = data["email"].lower().strip()
    password = data["password"]
    nombre = (data.get("nombre") or "").strip()
    apellido = (data.get("apellido") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    sexo = (data.get("sexo") or "").strip()

    rol_subtipo = (data.get("rol") or "paciente").strip().lower()
    idtu = _resolve_tipodeusuario(data.get("idtipousuario"))

    carnetidentidad = (data.get("carnetidentidad") or "").strip()
    fechanacimiento = data.get("fechanacimiento")
    direccion = (data.get("direccion") or "").strip()

    try:
        with transaction.atomic():
            # 1) Django User
            if User.objects.filter(username=email).exists():
                return Response({"detail": "Ya existe un usuario con ese email."}, status=status.HTTP_409_CONFLICT)
            dj_user = User.objects.create_user(username=email, email=email, password=password)
            if nombre or apellido:
                dj_user.first_name = nombre[:30]
                dj_user.last_name = apellido[:30]
                dj_user.save(update_fields=["first_name", "last_name"])

            # 2) 'usuario' base
            defaults_usuario = {
                "nombre": nombre or email.split("@")[0],
                "apellido": apellido,
                "telefono": telefono or None,
                "sexo": sexo or None,
                "idtipousuario_id": idtu,
            }
            usuario, created = Usuario.objects.get_or_create(
                correoelectronico=email,
                defaults=defaults_usuario,
            )
            if not created:
                changed = False
                if usuario.idtipousuario_id != idtu:
                    usuario.idtipousuario_id = idtu
                    changed = True
                for k, v in {
                    "nombre": nombre or usuario.nombre,
                    "apellido": apellido or usuario.apellido,
                    "telefono": telefono or usuario.telefono,
                    "sexo": sexo or usuario.sexo,
                }.items():
                    if getattr(usuario, k) != v:
                        setattr(usuario, k, v)
                        changed = True
                if changed:
                    usuario.save()

            # 3) Subtipo 1-1
            if rol_subtipo == "paciente":
                Paciente.objects.update_or_create(
                    codusuario=usuario,
                    defaults={
                        "carnetidentidad": carnetidentidad,
                        "fechanacimiento": fechanacimiento,
                        "direccion": direccion,
                    },
                )
            elif rol_subtipo == "odontologo":
                Odontologo.objects.get_or_create(codusuario=usuario)
            elif rol_subtipo == "recepcionista":
                Recepcionista.objects.get_or_create(codusuario=usuario)
            else:
                # fallback: paciente
                Paciente.objects.get_or_create(codusuario=usuario)

    except IntegrityError as e:
        return Response({"detail": "Error de integridad/DB.", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 4) Inicia sesión automáticamente
    login(request, dj_user)
    # opcional: compatibilidad con tu SessionAuth (expone email/id)
    request.session["auth"] = {"email": email, "auth_user_id": dj_user.id}
    request.session.save()

    return Response(
        {
            "ok": True,
            "message": "Usuario registrado e iniciado sesión.",
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
