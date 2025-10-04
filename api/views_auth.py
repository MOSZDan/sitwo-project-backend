# api/views_auth.py
from typing import Optional

from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings
from django.db import transaction, IntegrityError, DatabaseError

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView

from .models import Usuario, Paciente, Odontologo, Recepcionista, Bitacora
from .serializers import (
    UserNotificationSettingsSerializer,
    UsuarioMeSerializer,
)
from .serializers_auth import RegisterSerializer
from .serializers import NotificationPreferencesSerializer

User = get_user_model()


# ============================
# Utils
# ============================
def _client_ip(request):
    """
    Obtiene la IP del cliente de forma segura detrás de proxies.
    Siempre devuelve un valor (fallback "0.0.0.0") para no romper la bitácora.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "0.0.0.0"


# ============================
# CSRF
# ============================
@api_view(["GET"])
@permission_classes([AllowAny])  # público
@authentication_classes([])  # no exigir sesión
@ensure_csrf_cookie
def csrf_token(request):
    """Siembra cookie CSRF (csrftoken). Útil si luego usas endpoints con sesión/CSRF."""
    return Response({"detail": "CSRF cookie set"}, status=status.HTTP_200_OK)


def _resolve_tipodeusuario(idtipousuario: Optional[int]) -> int:
    """Compatibilidad legacy si llegara vacío (default paciente=2)."""
    return idtipousuario if idtipousuario else 2


# ============================
# Registro
# ============================
@api_view(["POST"])
@authentication_classes([])  # público
@permission_classes([AllowAny])  # público
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
                dj_user.first_name = nombre[:150]
                update_fields.append("first_name")
            if apellido:
                dj_user.last_name = apellido[:150]
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
                    usuario.idtipousuario_id = idtu
                    changed = True
                if nombre and usuario.nombre != nombre:
                    usuario.nombre = nombre
                    changed = True
                if apellido and usuario.apellido != apellido:
                    usuario.apellido = apellido
                    changed = True
                if telefono is not None and usuario.telefono != telefono:
                    usuario.telefono = telefono
                    changed = True
                if sexo is not None and usuario.sexo != sexo:
                    usuario.sexo = sexo
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
                    return Response({"carnetidentidad": "El carnet ya existe."}, status=status.HTTP_409_CONFLICT)
            elif rol_subtipo == "odontologo":
                Odontologo.objects.get_or_create(codusuario=usuario)
            elif rol_subtipo == "recepcionista":
                Recepcionista.objects.get_or_create(codusuario=usuario)
            elif rol_subtipo == "administrador":
                pass
            else:
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
# Login / Logout / User info
# ============================
@api_view(["POST"])
@authentication_classes([])  # público
@permission_classes([AllowAny])  # público
def auth_login(request):
    """
    Inicio de sesión con email/password
    Devuelve información del usuario y token de autenticación
    """
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password")
    if not email or not password:
        return Response({"detail": "Email y contraseña son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=email, password=password)
    if not user:
        return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        return Response({"detail": "Cuenta desactivada"}, status=status.HTTP_401_UNAUTHORIZED)

    token, _ = Token.objects.get_or_create(user=user)

    try:
        usuario = Usuario.objects.get(correoelectronico=email)

        # Log de login (tolerante a fallos: jamás rompe el login)
        try:
            Bitacora.objects.create(
                accion='login',
                descripcion=f'Login exitoso - {usuario.nombre} {usuario.apellido}',
                usuario=usuario,
                ip_address=_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                datos_adicionales={'email': email, 'metodo': 'manual_login_view'}
            )
        except Exception as log_error:
            # Importante: NO lanzar excepción aquí
            print(f"[Bitacora] No se pudo guardar el log de login: {log_error}")

        # Determinar subtipo
        subtipo = "usuario"
        if hasattr(usuario, "paciente"):
            subtipo = "paciente"
        elif hasattr(usuario, "odontologo"):
            subtipo = "odontologo"
        elif hasattr(usuario, "recepcionista"):
            subtipo = "recepcionista"
        elif usuario.idtipousuario_id == 1:
            subtipo = "administrador"

        return Response({
            "ok": True,
            "message": "Login exitoso",
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
                "recibir_notificaciones": usuario.recibir_notificaciones,
            }
        })
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado en el sistema"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
def auth_logout(request):
    """Cerrar sesión - elimina el token del usuario"""
    try:
        if hasattr(request.user, "auth_token"):
            request.user.auth_token.delete()
        return Response({"detail": "Sesión cerrada correctamente"}, status=status.HTTP_200_OK)
    except Exception:
        return Response({"detail": "Error al cerrar sesión"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def auth_user_info(request):
    """Información del usuario autenticado actual"""
    if not request.user.is_authenticated:
        return Response({"detail": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        usuario = Usuario.objects.get(correoelectronico=request.user.email)
        # Determinar subtipo
        subtipo = "usuario"
        if hasattr(usuario, "paciente"):
            subtipo = "paciente"
        elif hasattr(usuario, "odontologo"):
            subtipo = "odontologo"
        elif hasattr(usuario, "recepcionista"):
            subtipo = "recepcionista"
        elif usuario.idtipousuario_id == 1:
            subtipo = "administrador"
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

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
            },
        },
        status=status.HTTP_200_OK,
    )


# ============================
# Recuperación de contraseña
# ============================
@api_view(["POST"])
@authentication_classes([])  # público
@permission_classes([AllowAny])  # público
def password_reset_request(request):
    """
    Paso 1: Usuario envía su email -> se manda link de reset (HTML + texto).
    Respuesta genérica anti-enumeración SIEMPRE 200.
    """
    email = (request.data.get("email") or "").strip().lower()
    generic_msg = "Si el correo existe, enviamos un enlace para restablecer tu contraseña."

    if not email:
        return Response({"detail": "Email es requerido"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email__iexact=email).first()
    if user:
        # Generar token y uid
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"

        subject = "Recuperación de contraseña - Clínica Dental"
        text_content = f"Usa este link para cambiar tu contraseña: {reset_url}"
        html_content = f"""
        <p>Hola{(' ' + (user.first_name or '')) if getattr(user, 'first_name', '') else ''},</p>
        <p>Has solicitado recuperar tu contraseña. Haz clic en el siguiente enlace para continuar:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>Si no solicitaste este cambio, ignora este correo.</p>
        """
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            # Evitar 500 si email backend no está configurado:
            msg.send(fail_silently=True)
        except Exception:
            pass

    # Respuesta uniforme (exista o no el email)
    return Response({"ok": True, "message": generic_msg}, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([])  # público
@permission_classes([AllowAny])  # público
def password_reset_confirm(request):
    """
    Paso 2: Usuario envía uid + token + new_password
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

    return Response({"ok": True, "message": "Contraseña actualizada correctamente"}, status=status.HTTP_200_OK)


# ============================
# Preferencias de Usuario
# ============================
@api_view(["PATCH"])
def auth_user_settings_update(request):
    """
    Actualiza las preferencias del usuario autenticado.
    Por ahora, solo para activar/desactivar notificaciones.
    """
    if not request.user.is_authenticated:
        return Response({"detail": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        usuario_instance = Usuario.objects.get(correoelectronico=request.user.email)
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserNotificationSettingsSerializer(instance=usuario_instance, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "ok": True,
            "message": "Preferencias actualizadas.",
            "recibir_notificaciones": serializer.data['recibir_notificaciones']
            }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH"])
def notification_preferences(request):
    """
    GET: Obtiene las preferencias de notificación del usuario
    PATCH: Actualiza las preferencias de notificación del usuario
    """
    if not request.user.is_authenticated:
        return Response({"detail": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        usuario_instance = Usuario.objects.get(correoelectronico=request.user.email)
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        data = {
            "notificaciones_email": usuario_instance.notificaciones_email,
            "notificaciones_push": usuario_instance.notificaciones_push,
        }
        return Response(data, status=status.HTTP_200_OK)

    elif request.method == "PATCH":
        serializer = NotificationPreferencesSerializer(instance=usuario_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "ok": True,
                "message": "Preferencias de notificación actualizadas.",
                "notificaciones_email": serializer.data['notificaciones_email'],
                "notificaciones_push": serializer.data['notificaciones_push']
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================
# Perfil de Usuario (GET/PATCH)
# ============================
class UsuarioMeView(APIView):
    """
    GET   /api/usuario/me  -> devuelve la fila en `usuario` del usuario autenticado
    PATCH /api/usuario/me  -> actualiza campos permitidos; sincroniza auth_user.email si cambia `correoelectronico`
    Vincula por: auth_user.email == usuario.correoelectronico (case-insensitive)
    """
    permission_classes = [IsAuthenticated]

    def _resolve_email(self, request) -> str:
        email = (getattr(request.user, "email", "") or "").strip()
        if not email:
            username = (getattr(request.user, "username", "") or "").strip()
            if "@" in username:
                email = username
        return email

    def _get_row(self, request) -> Usuario:
        email = self._resolve_email(request)
        if not email:
            raise ObjectDoesNotExist("El usuario autenticado no tiene email.")
        try:
            return Usuario.objects.get(correoelectronico__iexact=email)
        except MultipleObjectsReturned:
            return Usuario.objects.filter(correoelectronico__iexact=email).order_by("codigo").first()

    def _serialize(self, u: Usuario) -> dict:
        return {
            "codigo": u.codigo,
            "nombre": u.nombre,
            "apellido": u.apellido,
            "correoelectronico": u.correoelectronico,
            "sexo": u.sexo,
            "telefono": u.telefono,
            "idtipousuario": u.idtipousuario_id,
            "recibir_notificaciones": u.recibir_notificaciones,
        }

    def get(self, request):
        try:
            u = self._get_row(request)
        except ObjectDoesNotExist:
            return Response({"detail": "No se encontró tu fila en 'usuario' (correo no coincide)."}, status=404)
        return Response(self._serialize(u))

    @transaction.atomic
    def patch(self, request):
        try:
            u = self._get_row(request)
        except ObjectDoesNotExist:
            return Response({"detail": "No se encontró tu fila en 'usuario' (correo no coincide)."}, status=404)

        ser = UsuarioMeSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        allowed = {"nombre", "apellido", "correoelectronico", "sexo", "telefono", "recibir_notificaciones"}

        # Evitar duplicar correos (la BD también lo asegura con unique=True)
        nuevo_correo = data.get("correoelectronico")
        if nuevo_correo and Usuario.objects.exclude(pk=u.pk).filter(correoelectronico__iexact=nuevo_correo).exists():
            return Response({"detail": "Ese correo ya está registrado."}, status=status.HTTP_400_BAD_REQUEST)

        # Asignar cambios permitidos
        for k, v in data.items():
            if k in allowed:
                setattr(u, k, v)
        u.save()

        # Si cambió correo, sincronizar auth_user
        if nuevo_correo:
            auth_user = User.objects.get(pk=request.user.pk)
            auth_user.email = nuevo_correo
            try:
                if getattr(auth_user, "username", None) and "@" in (auth_user.username or ""):
                    auth_user.username = nuevo_correo
                auth_user.save(update_fields=["email", "username"])
            except Exception:
                auth_user.save(update_fields=["email"])

        return Response(self._serialize(u), status=200)
