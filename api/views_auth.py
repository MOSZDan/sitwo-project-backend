# api/views_auth.py
from typing import Optional

from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.db import transaction, IntegrityError, DatabaseError

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

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
@authentication_classes([])  # público
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

            # Nombres (hasta 150 chars)
            update_fields = []
            if nombre:
                dj_user.first_name = nombre[:150];
                update_fields.append("first_name")
            if apellido:
                dj_user.last_name = apellido[:150];
                update_fields.append("last_name")
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
                    usuario.idtipousuario_id = idtu;
                    changed = True
                if nombre and usuario.nombre != nombre:
                    usuario.nombre = nombre;
                    changed = True
                if apellido and usuario.apellido != apellido:
                    usuario.apellido = apellido;
                    changed = True
                if telefono is not None and usuario.telefono != telefono:
                    usuario.telefono = telefono;
                    changed = True
                if sexo is not None and usuario.sexo != sexo:
                    usuario.sexo = sexo;
                    changed = True
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


# ============================
# Inicio de sesión
# ============================

@api_view(["POST"])
@authentication_classes([])  # público
@permission_classes([AllowAny])
def auth_login(request):
    """
    Inicio de sesión con email/password
    Devuelve información del usuario y token de autenticación
    """
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"detail": "Email y contraseña son requeridos"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Autenticar usuario (username=email en tu sistema)
    user = authenticate(username=email.lower().strip(), password=password)

    if not user:
        return Response(
            {"detail": "Credenciales inválidas"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"detail": "Cuenta desactivada"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Crear o obtener token
    token, created = Token.objects.get_or_create(user=user)

    # Obtener información del usuario del dominio
    try:
        usuario = Usuario.objects.get(correoelectronico=email.lower().strip())

        # Determinar el subtipo/rol del usuario
        subtipo = "usuario"  # default
        if hasattr(usuario, 'paciente'):
            subtipo = "paciente"
        elif hasattr(usuario, 'odontologo'):
            subtipo = "odontologo"
        elif hasattr(usuario, 'recepcionista'):
            subtipo = "recepcionista"
        elif usuario.idtipousuario_id == 1:  # asumiendo que 1 es admin
            subtipo = "administrador"

    except Usuario.DoesNotExist:
        # Si no existe en tabla Usuario, crear uno básico
        usuario = Usuario.objects.create(
            correoelectronico=email.lower().strip(),
            nombre=user.first_name or email.split("@")[0],
            apellido=user.last_name or "",
            idtipousuario_id=2  # paciente por defecto
        )
        subtipo = "paciente"

    return Response(
        {
            "ok": True,
            "message": "Inicio de sesión exitoso",
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
            },
            "usuario": {
                "codigo": usuario.codigo,
                "nombre": usuario.nombre,
                "apellido": usuario.apellido,
                "telefono": usuario.telefono,
                "sexo": usuario.sexo,
                "subtipo": subtipo,
                "idtipousuario": usuario.idtipousuario_id,
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
def auth_logout(request):
    """
    Cerrar sesión - elimina el token del usuario
    """
    try:
        # Eliminar token si existe
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        return Response(
            {"detail": "Sesión cerrada correctamente"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"detail": "Error al cerrar sesión"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET"])
def auth_user_info(request):
    """
    Obtener información del usuario autenticado actual
    """
    if not request.user.is_authenticated:
        return Response(
            {"detail": "No autenticado"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        usuario = Usuario.objects.get(correoelectronico=request.user.email)

        # Determinar subtipo
        subtipo = "usuario"
        if hasattr(usuario, 'paciente'):
            subtipo = "paciente"
        elif hasattr(usuario, 'odontologo'):
            subtipo = "odontologo"
        elif hasattr(usuario, 'recepcionista'):
            subtipo = "recepcionista"
        elif usuario.idtipousuario_id == 1:
            subtipo = "administrador"

    except Usuario.DoesNotExist:
        return Response(
            {"detail": "Usuario no encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        {
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            },
            "usuario": {
                "codigo": usuario.codigo,
                "nombre": usuario.nombre,
                "apellido": usuario.apellido,
                "telefono": usuario.telefono,
                "sexo": usuario.sexo,
                "subtipo": subtipo,
                "idtipousuario": usuario.idtipousuario_id,
            }
        },
        status=status.HTTP_200_OK
    )


# ============================
# Recuperación de contraseña
# ============================

@api_view(["POST"])
@authentication_classes([])  # público
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Paso 1: Usuario envía su email -> se manda link de reset (HTML + texto)
    """
    email = request.data.get("email")
    if not email:
        return Response({"detail": "Email es requerido"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # No revelamos si existe
        return Response({"detail": "Si el correo existe, se enviará un link"}, status=status.HTTP_200_OK)

    # Generar token y uid
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"

    # Enviar email HTML
    subject = "Recuperación de contraseña - Clínica Dental"
    text_content = f"Usa este link para cambiar tu contraseña: {reset_url}"
    html_content = f"""
    <p>Hola{(' ' + (user.first_name or '')) if getattr(user, 'first_name', '') else ''},</p>
    <p>Has solicitado recuperar tu contraseña. Haz clic en el siguiente enlace para continuar:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>Si no solicitaste este cambio, ignora este correo.</p>
    """

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    return Response({"detail": "Si el correo existe, se enviará un link"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([])  # público
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Paso 2: Usuario envía uid + token + nueva contraseña
    """
    uid = request.data.get("uid")
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    if not (uid and token and new_password):
        return Response({"detail": "Faltan datos"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError):
        return Response({"detail": "Usuario inválido"}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({"detail": "Token inválido o expirado"}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    return Response({"detail": "Contraseña actualizada correctamente"}, status=status.HTTP_200_OK)