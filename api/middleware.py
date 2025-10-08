# api/middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from .models import Bitacora, Usuario, Empresa
import json


def get_client_ip(request):
    """Obtiene la IP del cliente considerando proxies"""
    # Primero intentar headers de proxy
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
        return ip

    # Headers alternativos para diferentes proxies
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()

    # Header de Cloudflare
    cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_connecting_ip:
        return cf_connecting_ip.strip()

    # Si no hay proxies, usar REMOTE_ADDR
    remote_addr = request.META.get('REMOTE_ADDR')

    # Si estás en desarrollo local, simular una IP real
    if remote_addr in ['127.0.0.1', '::1', 'localhost']:
        return '192.168.1.100'  # IP simulada para desarrollo

    return remote_addr or '0.0.0.0'


def get_usuario_from_request(request):
    """Obtiene el usuario de negocio (Usuario) desde el request"""
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            email = getattr(request.user, 'email', None) or getattr(request.user, 'username', '')
            if email:
                return Usuario.objects.filter(correoelectronico__iexact=email.strip().lower()).first()
        except Usuario.DoesNotExist:
            pass
    return None


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware para identificar y establecer el tenant/empresa actual.
    Prioridad de identificación:
    1. Header HTTP X-Tenant-ID
    2. Usuario autenticado (empresa del usuario)
    3. Subdominio (futuro)
    """

    def process_request(self, request):
        empresa = None

        # Opción 1: Por header HTTP X-Tenant-Subdomain (enviado desde frontend)
        tenant_subdomain = request.META.get('HTTP_X_TENANT_SUBDOMAIN')
        if tenant_subdomain:
            try:
                empresa = Empresa.objects.get(subdomain__iexact=tenant_subdomain, activo=True)
            except Empresa.DoesNotExist:
                pass

        # Opción 2: Por header HTTP X-Tenant-ID
        if not empresa:
            tenant_id = request.META.get('HTTP_X_TENANT_ID')
            if tenant_id:
                try:
                    empresa = Empresa.objects.get(id=int(tenant_id))
                except (Empresa.DoesNotExist, ValueError):
                    pass

        # Opción 3: Por subdominio de la URL (fallback)
        if not empresa:
            host = request.get_host().split(':')[0]  # Eliminar puerto
            # Detectar subdominio (ej: norte.localhost → norte)
            if '.' in host:
                subdomain = host.split('.')[0]
                # Evitar que 'www' o 'localhost' sean considerados subdominios
                if subdomain not in ['www', 'localhost', '127']:
                    try:
                        empresa = Empresa.objects.get(subdomain__iexact=subdomain, activo=True)
                    except Empresa.DoesNotExist:
                        pass

        # Opción 4: Por usuario autenticado (fallback final)
        if not empresa:
            usuario = get_usuario_from_request(request)
            if usuario and usuario.empresa:
                empresa = usuario.empresa

        # Guardar la empresa en el request para uso posterior
        request.tenant = empresa
        request.tenant_id = empresa.id if empresa else None


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware para registrar automáticamente ciertos eventos en la bitácora
    EXCLUYE login para evitar duplicados
    """

    def process_response(self, request, response):
        # Solo registrar ciertos endpoints y métodos
        if self._should_audit(request, response):
            self._create_audit_log(request, response)
        return response

    def _should_audit(self, request, response):
        """Determina si se debe auditar esta request"""
        path = request.path_info
        method = request.method

        # Solo auditar requests exitosas (2xx) o redirects (3xx)
        if not (200 <= response.status_code < 400):
            return False

        # EXCLUIR endpoints de autenticación para evitar duplicados y bucles
        exclude_paths = [
            '/api/auth/login/',
            '/api/auth/csrf/',
            '/api/auth/user/',
            '/api/health/',
            '/api/db/',
        ]

        if any(path.startswith(exclude_path) for exclude_path in exclude_paths):
            return False

        # Auditar estos endpoints específicos
        audit_paths = [
            '/api/auth/logout/',
            '/api/auth/register/',
            '/api/consultas/',
            '/api/pacientes/',
            '/api/usuarios/',
        ]

        return any(path.startswith(audit_path) for audit_path in audit_paths)

    def _create_audit_log(self, request, response):
        """Crea el registro de auditoría"""
        try:
            path = request.path_info
            method = request.method
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            usuario = get_usuario_from_request(request)

            # Determinar la acción basada en la ruta y método
            accion, descripcion, modelo_afectado, objeto_id = self._determine_action(
                path, method, request, response
            )

            if accion:
                # Obtener empresa del request (establecida por TenantMiddleware)
                empresa = getattr(request, 'tenant', None)

                # Si no hay tenant en request, intentar obtener de usuario
                if not empresa and usuario and usuario.empresa:
                    empresa = usuario.empresa

                Bitacora.objects.create(
                    accion=accion,
                    descripcion=descripcion,
                    usuario=usuario,
                    empresa=empresa,  # Agregar empresa
                    ip_address=ip_address,
                    user_agent=user_agent,
                    modelo_afectado=modelo_afectado,
                    objeto_id=objeto_id,
                    datos_adicionales={
                        'path': path,
                        'method': method,
                        'status_code': response.status_code,
                        'source': 'middleware',
                        'tenant_id': empresa.id if empresa else None,
                        'tenant_nombre': empresa.nombre if empresa else None
                    }
                )
        except Exception as e:
            # No queremos que errores en auditoría rompan la aplicación
            print(f"Error en AuditMiddleware: {e}")

    def _determine_action(self, path, method, request, response):
        """Determina la acción a registrar basada en la ruta y método"""
        accion = None
        descripcion = ""
        modelo_afectado = None
        objeto_id = None

        if '/api/auth/logout/' in path and method == 'POST':
            accion = 'logout'
            descripcion = 'Usuario cerró sesión'

        elif '/api/auth/register/' in path and method == 'POST':
            accion = 'registro'
            descripcion = 'Nuevo usuario registrado'

        elif '/api/consultas/' in path:
            modelo_afectado = 'Consulta'
            if method == 'POST':
                accion = 'crear_cita'
                descripcion = 'Nueva cita creada'
            elif method in ['PUT', 'PATCH']:
                accion = 'modificar_cita'
                descripcion = 'Cita modificada'
                try:
                    objeto_id = int(path.split('/')[-2]) if path.endswith('/') else int(path.split('/')[-1])
                except (ValueError, IndexError):
                    pass
            elif method == 'DELETE':
                accion = 'eliminar_cita'
                descripcion = 'Cita eliminada'
                try:
                    objeto_id = int(path.split('/')[-2]) if path.endswith('/') else int(path.split('/')[-1])
                except (ValueError, IndexError):
                    pass

        elif '/api/pacientes/' in path:
            modelo_afectado = 'Paciente'
            if method == 'POST':
                accion = 'crear_paciente'
                descripcion = 'Nuevo paciente creado'
            elif method in ['PUT', 'PATCH']:
                accion = 'modificar_paciente'
                descripcion = 'Paciente modificado'

        elif '/api/usuarios/' in path:
            modelo_afectado = 'Usuario'
            if method == 'POST':
                accion = 'crear_usuario'
                descripcion = 'Nuevo usuario creado'
            elif method in ['PUT', 'PATCH']:
                accion = 'modificar_usuario'
                descripcion = 'Usuario modificado'
            elif method == 'DELETE':
                accion = 'eliminar_usuario'
                descripcion = 'Usuario eliminado'

        return accion, descripcion, modelo_afectado, objeto_id