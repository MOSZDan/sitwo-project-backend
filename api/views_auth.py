# api/views_auth.py
from typing import Optional

from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.db import transaction, IntegrityError

from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .serializers_auth import RegisterSerializer, LoginSerializer
from .models import Usuario, Paciente, Odontologo, Recepcionista, Tipodeusuario

User = get_user_model()



@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_token(request):
    """Siembra cookie CSRF (csrftoken). Llamar antes de POST/PUT/PATCH/DELETE."""
    return Response({"detail": "CSRF cookie set"})


from typing import Optional

def _resolve_tipodeusuario(idtipousuario: Optional[int]) -> int:
    """
    Si el body trae idtipousuario, úsalo.
    Si NO trae, usa 2 por defecto (catálogo: 'Paciente').
    """
    return idtipousuario if idtipousuario else 2


# dentro de api/views_auth.py, reemplaza COMPLETA la función auth_register por esta:

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def auth_register(request):
    """
    Registro por email/password:
      1) Crea Django User (email como username).
      2) Crea fila base en 'usuario' con idtipousuario (default=2 normal).
      3) Crea SUBTIPO 1-1 según 'rol' (default: paciente) y coloca datos de paciente.
      4) Inicia sesión.
    Body JSON: {
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

    rol_subtipo = (data.get("rol") or "paciente").strip().lower()   # default paciente
    idtu = _resolve_tipodeusuario(data.get("idtipousuario"))        # default=2 en helper

    # campos paciente (el serializer ya los validó si rol=patient)
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

            # 2) 'usuario' base (catálogo independiente del subtipo)
            usuario, created = Usuario.objects.get_or_create(
                correoelectronico=email,
                defaults={
                    "nombre": nombre or email.split("@")[0],
                    "apellido": apellido,
                    "telefono": telefono or None,
                    "sexo": sexo or None,
                    "idtipousuario_id": idtu,
                },
            )
            if not created:
                changed = False
                if usuario.idtipousuario_id != idtu:
                    usuario.idtipousuario_id = idtu; changed = True
                for k, v in {
                    "nombre": nombre or usuario.nombre,
                    "apellido": apellido or usuario.apellido,
                    "telefono": telefono or usuario.telefono,
                    "sexo": sexo or usuario.sexo,
                }.items():
                    if getattr(usuario, k) != v:
                        setattr(usuario, k, v); changed = True
                if changed:
                    usuario.save()

            # 3) Subtipo 1-1
            if rol_subtipo == "paciente":
                # El serializer ya verificó obligatoriedad + unicidad de CI
                pac_defaults = {
                    "carnetidentidad": carnetidentidad,
                    "fechanacimiento": fechanacimiento,
                    "direccion": direccion,
                }
                # update_or_create para respetar PK compartida
                Paciente.objects.update_or_create(codusuario=usuario, defaults=pac_defaults)

            elif rol_subtipo == "odontologo":
                Odontologo.objects.get_or_create(codusuario=usuario)
            elif rol_subtipo == "recepcionista":
                Recepcionista.objects.get_or_create(codusuario=usuario)
            else:
                # valor inesperado → caemos a paciente (con mínimos por si acaso)
                Paciente.objects.get_or_create(codusuario=usuario)

    except IntegrityError as e:
        return Response({"detail": "Error de integridad/DB.", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 4) Inicia sesión
    login(request, dj_user)

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
            "idtipousuario": idtu,  # 2 (normal) por defecto
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def auth_login(request):
    """Login por email/password (Django). Persiste cookie de sesión."""
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    email = data["email"].lower().strip()
    user = authenticate(request, username=email, password=data["password"])
    if not user:
        return Response({"detail": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    return Response({"ok": True, "user": {"id": user.id, "email": email}})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Devuelve info del usuario autenticado + match con tu tabla 'usuario' y subtipo."""
    u = request.user
    email = u.username
    data_usuario = None
    rol_detectado = None

    try:
        ux = Usuario.objects.select_related("idtipousuario").get(correoelectronico=email)
        data_usuario = {
            "codigo": ux.codigo,
            "nombre": ux.nombre,
            "apellido": ux.apellido,
            "telefono": ux.telefono,
            "sexo": ux.sexo,
            "idtipousuario": getattr(ux.idtipousuario, "id", None),
            "rol_catalogo": getattr(ux.idtipousuario, "rol", None),  # "admin" o "normal"
        }
        # Detectar subtipo por existencia de fila
        if Paciente.objects.filter(codusuario=ux).exists():
            rol_detectado = "paciente"
        elif Odontologo.objects.filter(codusuario=ux).exists():
            rol_detectado = "odontologo"
        elif Recepcionista.objects.filter(codusuario=ux).exists():
            rol_detectado = "recepcionista"
        else:
            rol_detectado = None
    except Usuario.DoesNotExist:
        pass

    return Response(
        {
            "id": u.id,
            "email": email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "rol": rol_detectado,
            "usuario": data_usuario,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """Cierra la sesión (borra cookie)."""
    logout(request)
    return Response({"ok": True})


# ---------- Admin: cambiar TipoDeUsuario (1=admin, 2=normal) ----------
class UpdateTipoUsuarioSerializer(serializers.Serializer):
    idtipousuario = serializers.IntegerField(min_value=1)


@api_view(["PATCH"])
@permission_classes([IsAdminUser])  # solo staff/superuser
def update_user_tipo(request, codigo: int):
    """
    Cambia el catálogo TipoDeUsuario de un 'usuario' existente.
    URL: PATCH /api/auth/users/<codigo>/tipo/
    Body: { "idtipousuario": 1 | 2 }
    """
    s = UpdateTipoUsuarioSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    idtu = s.validated_data["idtipousuario"]

    # Validar que el tipo exista
    if not Tipodeusuario.objects.filter(id=idtu).exists():
        return Response({"detail": "idtipousuario inválido."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        ux = Usuario.objects.get(codigo=codigo)
    except Usuario.DoesNotExist:
        return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    ux.idtipousuario_id = idtu
    ux.save(update_fields=["idtipousuario"])
    return Response({"ok": True, "codigo": ux.codigo, "idtipousuario": idtu})
