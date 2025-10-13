from django.utils import timezone
from django.db.models import Q

from api.models import Usuario, BloqueoUsuario


def _resolver_usuario_api(desde):
    """
    Acepta:
      - instancia de api.Usuario
      - instancia de auth.User (user.email)
      - string (email)
      - dict con 'email' o 'correoelectronico'
    Retorna instancia de api.Usuario o None.
    """
    if desde is None:
        return None

    # Ya es un Usuario de dominio
    if isinstance(desde, Usuario):
        return desde

    # Intentar por atributos comunes
    email = None
    if isinstance(desde, str):
        email = desde
    elif isinstance(desde, dict):
        email = desde.get("email") or desde.get("correoelectronico")
    else:
        # auth.User u otro objeto con email
        email = getattr(desde, "email", None) or getattr(desde, "correoelectronico", None)

    if not email:
        return None

    return Usuario.objects.filter(correoelectronico__iexact=email).first()


def esta_bloqueado_y_motivo(desde) -> tuple[bool, str | None]:
    """
    Verifica si el usuario tiene un bloqueo vigente (activo y sin fin o con fin futuro).
    Retorna (True, mensaje) si está bloqueado, (False, None) si no.

    'desde' puede ser Usuario, auth.User, email (str) o dict con email.
    """
    usuario = _resolver_usuario_api(desde)
    if not usuario:
        # Si no existe en api.Usuario, no se bloquea.
        return False, None

    ahora = timezone.now()
    bloqueo = (
        BloqueoUsuario.objects.filter(
            usuario=usuario,
            activo=True,
        )
        .filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gt=ahora))
        .order_by("-fecha_inicio")
        .first()
    )

    if bloqueo:
        msg = bloqueo.motivo or (f"Usuario bloqueado hasta {bloqueo.fecha_fin}." if bloqueo.fecha_fin else "Usuario bloqueado.")
        return True, msg

    return False, None