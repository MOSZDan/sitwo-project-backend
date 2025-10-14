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
    try:
        # Verificar si hay token en el header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            from rest_framework.authtoken.models import Token
            token_key = auth_header.split(' ')[1]
            try:
                token = Token.objects.select_related('user').get(key=token_key)
                request.user = token.user
                print(f"[Token] Usuario autenticado: {token.user}")
            except Token.DoesNotExist:
                print("[Token] Token no encontrado")
                return None

        if hasattr(request, 'user') and request.user.is_authenticated:
            print(f"[Auth] Usuario autenticado: {request.user}")
            # Primero intentar por correo electrónico
            email = getattr(request.user, 'email', None) or getattr(request.user, 'username', '')
            if email:
                usuario = Usuario.objects.select_related('empresa').filter(
                    correoelectronico__iexact=email.strip().lower()
                ).first()
                if usuario:
                    print(f"[Usuario encontrado] Email: {email}, Empresa: {usuario.empresa}")
                    return usuario
                else:
                    print(f"[Usuario no encontrado] Email: {email}")

        print("[Auth] Usuario no autenticado o no encontrado")
        return None
    except Exception as e:
        print(f"[Error] Excepción en get_usuario_from_request: {str(e)}")
        return None


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware para identificar y establecer el tenant/empresa actual.
    Prioridad de identificación:
    1. Usuario autenticado (empresa del usuario)
    2. Header HTTP X-Tenant-ID
    3. Subdominio
    """

    def process_request(self, request):
        # Excluir endpoints públicos del tenant middleware
        path = request.path_info
        public_paths = [
            '/api/public/',
            '/api/health/',
            '/api/ping/',
            '/api/db/',
        ]

        # Si es un endpoint público, no requerir tenant
        if any(path.startswith(public_path) for public_path in public_paths):
            request.tenant = None
            request.tenant_id = None
            return

        empresa = None
        print("\n=== TenantMiddleware processing request ===")
        print(f"Path: {request.path}")
        print(f"Headers: {request.headers.get('Authorization', 'No Auth header')}")

        # Si es una ruta de autenticación, no requerimos tenant
        if request.path.startswith('/api/auth/'):
            print("Ruta de autenticación - No se requiere tenant")
            return None

        # Si hay token, intentar autenticar al usuario
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            print("[Auth] Token encontrado, procesando...")
        else:
            print("[Auth] No se encontró token válido")

        # Opción 1: Por usuario autenticado (principal método)
        if getattr(request.user, 'is_authenticated', False):
            usuario = get_usuario_from_request(request)
            if usuario and usuario.empresa:
                empresa = usuario.empresa
                print(f"Tenant encontrado por usuario: {empresa}")

        # Opción 2: Por header HTTP X-Tenant-Subdomain
        if not empresa:
            tenant_subdomain = request.META.get('HTTP_X_TENANT_SUBDOMAIN')
            if tenant_subdomain:
                try:
                    empresa = Empresa.objects.get(subdomain__iexact=tenant_subdomain, activo=True)
                    print(f"Tenant encontrado por subdomain: {empresa}")
                except Empresa.DoesNotExist:
                    print(f"No se encontró tenant para subdomain: {tenant_subdomain}")
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

        # Intentar obtener el usuario y su empresa
        usuario = get_usuario_from_request(request)
        if usuario and usuario.empresa:
            empresa = usuario.empresa
            print(f"[OK] Empresa encontrada por usuario: {empresa}")

        # Si no se encontró empresa por usuario, intentar por headers
        if not empresa:
            tenant_id = request.META.get('HTTP_X_TENANT_ID')
            if tenant_id:
                try:
                    empresa = Empresa.objects.get(id=tenant_id)
                    print(f"[OK] Empresa encontrada por header: {empresa}")
                except Empresa.DoesNotExist:
                    print(f"[ERROR] No se encontró empresa con ID: {tenant_id}")

        # Asignar la empresa al request
        request.tenant = empresa
        request.tenant_id = empresa.id if empresa else None

        # Para endpoints que requieren tenant, asegurarse de que exista
        if request.path.startswith('/api/') and not request.path.startswith('/api/auth/'):
            if not empresa:
                print("[ERROR] No se pudo determinar el tenant")
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'No se pudo determinar la empresa',
                    'detail': 'Se requiere un tenant válido para esta operación',
                    'debug_info': {
                        'path': request.path,
                        'token': bool(auth_header.startswith('Token ')),
                        'email': getattr(request.user, 'email', None),
                        'headers': dict(request.headers)
                    }
                }, status=400)
            else:
                print(f"[OK] Tenant configurado correctamente: {empresa}")

        return None


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

                from django.utils import timezone
                
                Bitacora.objects.create(
                    accion=accion,
                    usuario=usuario,
                    empresa=empresa,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    tabla_afectada=modelo_afectado,
                    registro_id=objeto_id,
                    valores_anteriores={
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