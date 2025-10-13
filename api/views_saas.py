# api/views_saas.py
"""
Vistas públicas para el registro y gestión de empresas en el modelo SaaS.
Estos endpoints NO requieren autenticación y son utilizados por el frontend público.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
import secrets
import string

from .models import Empresa, Usuario, Tipodeusuario, Paciente
from .serializers import (
    RegistroEmpresaSerializer,
    ValidarSubdominioSerializer,
    EmpresaPublicSerializer
)


def generar_password_temporal():
    """Genera una contraseña temporal segura de 12 caracteres"""
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    return ''.join(secrets.choice(caracteres) for _ in range(12))


@api_view(['POST'])
@permission_classes([AllowAny])  # Este endpoint es PÚBLICO
def registrar_empresa(request):
    """
    Endpoint público para registrar una nueva empresa (cliente SaaS).

    POST /api/public/registrar-empresa/

    Body:
    {
        "nombre_empresa": "Clínica Dental Norte",
        "subdomain": "clinica-norte",
        "nombre_admin": "Juan",
        "apellido_admin": "Pérez",
        "email_admin": "juan@clinica-norte.com",
        "telefono_admin": "+591 12345678",
        "sexo_admin": "Masculino"
    }

    Respuesta exitosa (201):
    {
        "ok": true,
        "message": "Empresa registrada exitosamente",
        "empresa": {
            "id": 4,
            "nombre": "Clínica Dental Norte",
            "subdomain": "clinica-norte",
            "activo": true
        },
        "admin": {
            "codigo": 123,
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan@clinica-norte.com"
        },
        "url_acceso": "https://clinica-norte.tusoftware.com",
        "password_temporal": "AbC123!@#XyZ"
    }
    """
    serializer = RegistroEmpresaSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            "ok": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    try:
        with transaction.atomic():
            # 1. Crear la empresa
            empresa = Empresa.objects.create(
                nombre=data['nombre_empresa'],
                subdomain=data['subdomain'].lower(),
                activo=True
            )

            # 2. Obtener rol de Administrador (id=1)
            try:
                rol_admin = Tipodeusuario.objects.get(id=1)
            except Tipodeusuario.DoesNotExist:
                # Si no existe, crearlo
                rol_admin = Tipodeusuario.objects.create(
                    id=1,
                    rol='Administrador',
                    descripcion='Usuario administrador del sistema',
                    empresa=None  # Los roles pueden ser globales o por empresa
                )

            # 3. Generar contraseña temporal
            password_temporal = generar_password_temporal()

            # 4. Crear usuario administrador
            usuario_admin = Usuario.objects.create(
                nombre=data['nombre_admin'],
                apellido=data['apellido_admin'],
                correoelectronico=data['email_admin'].lower(),
                telefono=data.get('telefono_admin', ''),
                sexo=data.get('sexo_admin', ''),
                idtipousuario=rol_admin,
                empresa=empresa,
                recibir_notificaciones=True,
                notificaciones_email=True,
                notificaciones_push=False
            )

            # 5. Crear usuario en auth de Django (para login)
            from django.contrib.auth import get_user_model
            User = get_user_model()

            django_user = User.objects.create(
                username=data['email_admin'].lower(),
                email=data['email_admin'].lower(),
                first_name=data['nombre_admin'],
                last_name=data['apellido_admin'],
                is_active=True,
                is_staff=True,  # Admin tiene acceso al panel Django admin
                password=make_password(password_temporal)
            )

            # 6. Enviar email de bienvenida con credenciales
            try:
                url_acceso = f"https://{empresa.subdomain}.{settings.SAAS_BASE_DOMAIN}"

                subject = f"¡Bienvenido a {settings.CLINIC_INFO.get('name', 'Nuestro Sistema')}!"
                message = f"""
Hola {usuario_admin.nombre},

¡Gracias por registrarte en nuestro sistema!

Tu empresa "{empresa.nombre}" ha sido creada exitosamente.

CREDENCIALES DE ACCESO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URL de acceso: {url_acceso}
Usuario: {usuario_admin.correoelectronico}
Contraseña temporal: {password_temporal}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ IMPORTANTE: Por razones de seguridad, te recomendamos cambiar tu contraseña después del primer inicio de sesión.

PRÓXIMOS PASOS:
1. Accede al sistema usando el enlace y credenciales proporcionados
2. Cambia tu contraseña en la sección de perfil
3. Configura los datos de tu clínica
4. Crea usuarios adicionales (odontólogos, recepcionistas, etc.)
5. Comienza a registrar pacientes y agendar citas

Si tienes alguna pregunta o necesitas ayuda, no dudes en contactarnos.

¡Bienvenido a bordo!

Equipo de {settings.CLINIC_INFO.get('name', 'Soporte')}
{settings.CLINIC_INFO.get('email', '')}
{settings.CLINIC_INFO.get('phone', '')}
                """

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [usuario_admin.correoelectronico],
                    fail_silently=False
                )
                email_enviado = True
            except Exception as e:
                print(f"Error al enviar email de bienvenida: {e}")
                email_enviado = False

            # 7. Respuesta exitosa
            return Response({
                "ok": True,
                "message": "Empresa registrada exitosamente",
                "empresa": EmpresaPublicSerializer(empresa).data,
                "admin": {
                    "codigo": usuario_admin.codigo,
                    "nombre": usuario_admin.nombre,
                    "apellido": usuario_admin.apellido,
                    "email": usuario_admin.correoelectronico
                },
                "url_acceso": url_acceso,
                "password_temporal": password_temporal,
                "email_enviado": email_enviado,
                "instrucciones": "Revisa tu correo electrónico para las credenciales de acceso. Si no lo recibes, guarda la contraseña temporal mostrada aquí."
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "ok": False,
            "message": "Error al registrar la empresa",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # Endpoint público
def validar_subdomain(request):
    """
    Valida si un subdominio está disponible.

    POST /api/public/validar-subdomain/

    Body:
    {
        "subdomain": "mi-clinica"
    }

    Respuesta exitosa (200):
    {
        "ok": true,
        "disponible": true,
        "subdomain": "mi-clinica",
        "mensaje": "El subdominio está disponible"
    }

    Respuesta cuando NO está disponible (200):
    {
        "ok": true,
        "disponible": false,
        "subdomain": "norte",
        "mensaje": "Este subdominio ya está en uso."
    }
    """
    serializer = ValidarSubdominioSerializer(data=request.data)

    if serializer.is_valid():
        return Response({
            "ok": True,
            "disponible": True,
            "subdomain": serializer.validated_data['subdomain'],
            "mensaje": "El subdominio está disponible"
        }, status=status.HTTP_200_OK)
    else:
        # El subdominio no está disponible o tiene formato inválido
        error_message = list(serializer.errors.get('subdomain', ['Subdominio no disponible']))[0]

        return Response({
            "ok": True,
            "disponible": False,
            "subdomain": request.data.get('subdomain', ''),
            "mensaje": error_message
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])  # Endpoint público
def info_sistema(request):
    """
    Devuelve información pública del sistema.
    Útil para mostrar en la landing page.

    GET /api/public/info/

    Respuesta:
    {
        "ok": true,
        "sistema": {
            "nombre": "Clínica Dental SaaS",
            "version": "1.0.0",
            "caracteristicas": [...],
            "planes": [...]
        },
        "estadisticas": {
            "empresas_activas": 15,
            "años_experiencia": 5
        }
    }
    """
    total_empresas = Empresa.objects.filter(activo=True).count()

    return Response({
        "ok": True,
        "sistema": {
            "nombre": settings.CLINIC_INFO.get('name', 'Sistema de Gestión Dental'),
            "descripcion": "Sistema completo para gestión de clínicas dentales",
            "caracteristicas": [
                "Gestión de pacientes",
                "Agendamiento de citas",
                "Historias clínicas electrónicas",
                "Facturación y pagos",
                "Reportes y estadísticas",
                "Multi-usuario con roles",
                "Notificaciones automáticas",
                "Sistema multi-tenant (cada clínica tiene su propia base de datos aislada)"
            ],
            "planes": [
                {
                    "nombre": "Básico",
                    "precio_mensual": 29.99,
                    "caracteristicas": [
                        "Hasta 100 pacientes",
                        "1 odontólogo",
                        "Soporte por email"
                    ]
                },
                {
                    "nombre": "Profesional",
                    "precio_mensual": 59.99,
                    "caracteristicas": [
                        "Pacientes ilimitados",
                        "Hasta 5 odontólogos",
                        "Soporte prioritario",
                        "Reportes avanzados"
                    ]
                },
                {
                    "nombre": "Enterprise",
                    "precio_mensual": 99.99,
                    "caracteristicas": [
                        "Todo ilimitado",
                        "Odontólogos ilimitados",
                        "Soporte 24/7",
                        "Personalización",
                        "API access"
                    ]
                }
            ]
        },
        "estadisticas": {
            "empresas_activas": total_empresas,
            "años_experiencia": 5
        },
        "contacto": {
            "email": settings.CLINIC_INFO.get('email', ''),
            "telefono": settings.CLINIC_INFO.get('phone', ''),
            "direccion": settings.CLINIC_INFO.get('address', '')
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])  # Endpoint público
def verificar_empresa_por_subdomain(request, subdomain):
    """
    Verifica si una empresa existe y está activa por su subdominio.
    Útil para validar antes de mostrar el login.

    GET /api/public/empresa/{subdomain}/

    Respuesta exitosa (200):
    {
        "ok": true,
        "existe": true,
        "empresa": {
            "nombre": "Clínica Dental Norte",
            "subdomain": "norte",
            "activo": true
        }
    }

    Respuesta cuando no existe (404):
    {
        "ok": false,
        "existe": false,
        "mensaje": "Empresa no encontrada"
    }
    """
    try:
        empresa = Empresa.objects.get(subdomain__iexact=subdomain, activo=True)
        return Response({
            "ok": True,
            "existe": True,
            "empresa": EmpresaPublicSerializer(empresa).data
        }, status=status.HTTP_200_OK)
    except Empresa.DoesNotExist:
        return Response({
            "ok": False,
            "existe": False,
            "mensaje": "Empresa no encontrada o inactiva"
        }, status=status.HTTP_404_NOT_FOUND)
