from django.http import HttpResponseForbidden
from .models import Usuario

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtener el dominio de la petición
        domain = request.get_host().split(':')[0].lower()

        # Establecer el tenant basado en el dominio
        # El tenant será 'None' para el dominio principal
        parts = domain.split('.')
        tenant = parts[0] if len(parts) > 2 else None
        request.tenant = tenant

        # Si el usuario está autenticado y hay un tenant, verificar acceso
        if request.user.is_authenticated and tenant:
            # Excluir rutas que no necesitan validación de tenant
            if not any(path in request.path for path in ['/admin/', '/static/', '/media/']):
                # Verificar si el usuario pertenece a la empresa (tenant)
                usuario = Usuario.objects.filter(
                    correoelectronico=request.user.email,
                    empresa__iexact=tenant  # Usar iexact para comparación case-insensitive
                ).exists()

                if not usuario:
                    return HttpResponseForbidden("No tienes acceso a esta empresa")

        response = self.get_response(request)
        return response
