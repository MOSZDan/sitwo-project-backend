from django.http import HttpResponseForbidden
from .models import Usuario, Empresa
import logging

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """
    Middleware para Multi-Tenancy basado en subdominios.

    Identifica la empresa (tenant) según el subdominio de la petición y:
    1. Resuelve el objeto Empresa desde la BD
    2. Lo almacena en request.tenant
    3. Valida que usuarios autenticados pertenezcan a su empresa
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtener el dominio de la petición
        domain = request.get_host().split(':')[0].lower()

        # PRIORIDAD 1: Leer header del frontend (desarrollo local)
        # El frontend envía X-Tenant-Subdomain cuando detecta un subdomain
        subdomain_from_header = request.headers.get('X-Tenant-Subdomain')

        # PRIORIDAD 2: Extraer subdominio del dominio del request
        # Ejemplo: norte.notificct.dpdns.org -> subdomain = "norte"
        # Ejemplo: notificct.dpdns.org -> subdomain = None (dominio público)
        # Ejemplo: localhost -> subdomain = None
        parts = domain.split('.')
        subdomain_from_domain = parts[0] if len(parts) > 2 else None

        # Usar header si está disponible, sino usar domain
        subdomain = subdomain_from_header or subdomain_from_domain

        # Resolver el objeto Empresa desde el subdominio
        tenant_empresa = None
        if subdomain and subdomain not in ['www', 'api']:  # Ignorar subdominios especiales
            try:
                tenant_empresa = Empresa.objects.get(
                    subdomain__iexact=subdomain,
                    activo=True
                )
                logger.debug(f"[TenantMiddleware] Tenant resuelto: {tenant_empresa.nombre} (subdomain: {subdomain})")
            except Empresa.DoesNotExist:
                logger.warning(f"[TenantMiddleware] Subdominio '{subdomain}' no encontrado o inactivo")
                # No hacer nada, tenant_empresa será None
            except Empresa.MultipleObjectsReturned:
                logger.error(f"[TenantMiddleware] Múltiples empresas con subdomain '{subdomain}' - ERROR DE CONFIGURACIÓN")
                # Tomar la primera activa como fallback
                tenant_empresa = Empresa.objects.filter(
                    subdomain__iexact=subdomain,
                    activo=True
                ).first()

        # Guardar el objeto Empresa en request.tenant (NO el string)
        request.tenant = tenant_empresa

        # VALIDACIÓN DE SEGURIDAD: Si el usuario está autenticado y hay un tenant,
        # verificar que el usuario pertenece a esa empresa
        if request.user.is_authenticated and tenant_empresa:
            # Excluir rutas públicas que no necesitan validación de tenant
            excluded_paths = [
                '/admin/',
                '/static/',
                '/media/',
                '/api/auth/login',
                '/api/auth/register',
                '/api/auth/csrf',
                '/api/health',
                '/api/db_health',
                '/api/auth/logout',
                '/api/auth/me',
                '/api/ping',
                '/api/public/',  # Rutas públicas de SaaS (registro de empresas, Stripe, etc.)
            ]

            # Si la ruta requiere validación de tenant
            if not any(request.path.startswith(path) for path in excluded_paths):
                # Verificar si el usuario pertenece a la empresa del tenant
                try:
                    # Buscar el usuario en la tabla Usuario (modelo de negocio)
                    usuario = Usuario.objects.filter(
                        correoelectronico__iexact=request.user.email,
                        empresa=tenant_empresa  # Comparar objeto con objeto
                    ).first()

                    if not usuario:
                        # Log detallado para debugging
                        logger.warning(
                            f"[TenantMiddleware] Acceso denegado: usuario '{request.user.email}' "
                            f"intentó acceder a empresa '{tenant_empresa.nombre}' (ID: {tenant_empresa.id}) "
                            f"sin pertenecer a ella. Path: {request.path}"
                        )

                        # Verificar si el usuario existe en otra empresa
                        usuario_otra_empresa = Usuario.objects.filter(
                            correoelectronico__iexact=request.user.email
                        ).select_related('empresa').first()

                        if usuario_otra_empresa:
                            logger.warning(
                                f"[TenantMiddleware] El usuario '{request.user.email}' pertenece a "
                                f"'{usuario_otra_empresa.empresa.nombre}' (subdomain: {usuario_otra_empresa.empresa.subdomain})"
                            )
                        else:
                            logger.error(
                                f"[TenantMiddleware] El usuario '{request.user.email}' NO existe en la tabla Usuario"
                            )

                        return HttpResponseForbidden(
                            "Acceso denegado: No tienes permisos para acceder a esta empresa. "
                            f"Por favor accede a través del subdominio correcto."
                        )
                except Exception as e:
                    logger.error(f"[TenantMiddleware] Error verificando pertenencia a empresa: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return HttpResponseForbidden("Error de validación de acceso")

        response = self.get_response(request)
        return response
