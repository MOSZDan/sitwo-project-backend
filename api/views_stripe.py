# api/views_stripe.py
"""
Vistas para integración con Stripe - Procesamiento de pagos
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
import secrets
import string
import stripe

from .models import Empresa, Usuario, Tipodeusuario
from .serializers import RegistroEmpresaSerializer, EmpresaPublicSerializer
from .views_saas import generar_password_temporal

# Configurar Stripe con la clave secreta
stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([AllowAny])
def create_payment_intent(request):
    """
    Crea un Payment Intent de Stripe para procesar el pago.

    POST /api/public/create-payment-intent/

    Body:
    {
        "email": "cliente@example.com",
        "nombre_empresa": "Mi Clínica Dental"
    }

    Respuesta:
    {
        "clientSecret": "pi_xxx_secret_xxx",
        "price": 99,
        "customerId": "cus_xxx"
    }
    """
    try:
        email = request.data.get('email')
        nombre_empresa = request.data.get('nombre_empresa')

        if not email or not nombre_empresa:
            return Response({
                "ok": False,
                "message": "Email y nombre de empresa son requeridos"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Precio del plan (puedes hacerlo dinámico si tienes múltiples planes)
        # Por ahora es un precio fijo de $99/mes
        price_amount = int(settings.STRIPE_PRICE_AMOUNT * 100)  # Stripe usa centavos

        # Buscar o crear el Customer en Stripe
        customers = stripe.Customer.list(email=email.lower(), limit=1)

        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(
                email=email.lower(),
                metadata={
                    'nombre_empresa': nombre_empresa,
                }
            )

        # Crear Payment Intent asociado al Customer
        intent = stripe.PaymentIntent.create(
            amount=price_amount,
            currency=settings.STRIPE_CURRENCY,
            customer=customer.id,  # Asociar al Customer
            automatic_payment_methods={'enabled': True},
            setup_future_usage='off_session',  # Permitir uso futuro del PaymentMethod
            metadata={
                'email': email,
                'nombre_empresa': nombre_empresa,
            },
            description=f"Suscripción mensual - {nombre_empresa}",
            receipt_email=email,
        )

        return Response({
            "clientSecret": intent['client_secret'],
            "price": settings.STRIPE_PRICE_AMOUNT,
            "customerId": customer.id  # Retornar el ID del customer
        }, status=status.HTTP_200_OK)

    except stripe.StripeError as e:
        return Response({
            "ok": False,
            "message": f"Error de Stripe: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "ok": False,
            "message": f"Error al crear payment intent: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def registrar_empresa_con_pago(request):
    """
    Registra una empresa después de confirmar el pago con Stripe.

    POST /api/public/registrar-empresa-pago/

    Body:
    {
        "nombre_empresa": "Clínica Dental Norte",
        "subdomain": "clinica-norte",
        "nombre_admin": "Juan",
        "apellido_admin": "Pérez",
        "email_admin": "juan@clinica-norte.com",
        "telefono_admin": "+591 12345678",
        "sexo_admin": "Masculino",
        "payment_method_id": "pm_xxx"
    }
    """
    serializer = RegistroEmpresaSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            "ok": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    payment_method_id = request.data.get('payment_method_id')

    if not payment_method_id:
        return Response({
            "ok": False,
            "message": "payment_method_id es requerido"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # 1. Crear o recuperar cliente en Stripe
            try:
                # Buscar si ya existe un cliente con este email
                customers = stripe.Customer.list(email=data['email_admin'].lower(), limit=1)

                if customers.data:
                    customer = customers.data[0]
                else:
                    # Crear nuevo cliente en Stripe sin el payment method
                    customer = stripe.Customer.create(
                        email=data['email_admin'].lower(),
                        name=f"{data['nombre_admin']} {data['apellido_admin']}",
                        metadata={
                            'empresa': data['nombre_empresa'],
                            'subdomain': data['subdomain']
                        }
                    )

                # Adjuntar el PaymentMethod al Customer (para nuevos y existentes)
                try:
                    stripe.PaymentMethod.attach(
                        payment_method_id,
                        customer=customer.id
                    )

                    # Establecer como método de pago predeterminado
                    stripe.Customer.modify(
                        customer.id,
                        invoice_settings={'default_payment_method': payment_method_id}
                    )
                except stripe.InvalidRequestError as e:
                    # Si el payment method ya está adjunto, solo establecerlo como predeterminado
                    if 'already been attached' in str(e).lower():
                        stripe.Customer.modify(
                            customer.id,
                            invoice_settings={'default_payment_method': payment_method_id}
                        )
                    else:
                        # Si es otro error (como el que estás experimentando), lanzar excepción
                        raise

                # Crear suscripción usando el Price ID configurado en settings
                # Nota: El Price ya fue creado en Stripe Dashboard
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': settings.STRIPE_PRICE_ID}],
                    trial_period_days=14,  # 14 días gratis
                    metadata={
                        'empresa': data['nombre_empresa'],
                        'subdomain': data['subdomain']
                    }
                )

            except stripe.StripeError as e:
                return Response({
                    "ok": False,
                    "message": f"Error al procesar el pago: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 2. Crear la empresa en la BD
            empresa = Empresa.objects.create(
                nombre=data['nombre_empresa'],
                subdomain=data['subdomain'].lower(),
                activo=True,
                stripe_customer_id=customer.id,
                stripe_subscription_id=subscription.id
            )

            # 3. Obtener o crear rol de Administrador
            try:
                rol_admin = Tipodeusuario.objects.get(id=1)
            except Tipodeusuario.DoesNotExist:
                rol_admin = Tipodeusuario.objects.create(
                    id=1,
                    rol='Administrador',
                    descripcion='Usuario administrador del sistema',
                    empresa=None
                )

            # 4. Generar contraseña temporal
            password_temporal = generar_password_temporal()

            # 5. Crear usuario administrador
            # Convertir sexo al formato esperado por la BD (M/F en lugar de Masculino/Femenino)
            sexo_admin = data.get('sexo_admin', '')
            if sexo_admin:
                sexo_bd = 'M' if sexo_admin.lower().startswith('m') else ('F' if sexo_admin.lower().startswith('f') else None)
            else:
                sexo_bd = None

            usuario_admin = Usuario.objects.create(
                nombre=data['nombre_admin'],
                apellido=data['apellido_admin'],
                correoelectronico=data['email_admin'].lower(),
                telefono=data.get('telefono_admin', ''),
                sexo=sexo_bd,
                idtipousuario=rol_admin,
                empresa=empresa,
                recibir_notificaciones=True,
                notificaciones_email=True,
                notificaciones_push=False
            )

            # 6. Crear usuario en auth de Django
            from django.contrib.auth import get_user_model
            User = get_user_model()

            django_user = User.objects.create(
                username=data['email_admin'].lower(),
                email=data['email_admin'].lower(),
                first_name=data['nombre_admin'],
                last_name=data['apellido_admin'],
                is_active=True,
                is_staff=True,
                password=make_password(password_temporal)
            )

            # 7. Preparar información de la suscripción para email y respuesta
            from datetime import datetime, timezone

            # Obtener fecha del próximo cobro (si existe)
            if hasattr(subscription, 'current_period_end') and subscription.current_period_end:
                # Convertir timestamp de Stripe a fecha legible
                next_billing_date = datetime.fromtimestamp(
                    subscription.current_period_end,
                    tz=timezone.utc
                ).strftime('%d/%m/%Y')
            else:
                # Si está en trial, calcular 14 días desde ahora
                from datetime import timedelta
                next_billing_date = (datetime.now(timezone.utc) + timedelta(days=14)).strftime('%d/%m/%Y')

            # 8. Enviar email de bienvenida
            try:
                dominio_base = settings.SAAS_BASE_DOMAIN
                url_acceso = f"https://{empresa.subdomain}.{dominio_base}"

                subject = f"¡Bienvenido a {settings.CLINIC_INFO.get('name', 'Nuestro Sistema')}!"
                message = f"""
Hola {usuario_admin.nombre},

¡Gracias por suscribirte a nuestro sistema!

Tu empresa "{empresa.nombre}" ha sido creada exitosamente y tu pago ha sido procesado.

CREDENCIALES DE ACCESO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URL de acceso: {url_acceso}
Usuario: {usuario_admin.correoelectronico}
Contraseña temporal: {password_temporal}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 INFORMACIÓN DE PAGO:
- Plan: Plan Completo
- Precio: ${settings.STRIPE_PRICE_AMOUNT}/mes
- Período de prueba: 14 días gratis
- Próximo cobro: {next_billing_date}

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

            # 9. Respuesta exitosa
            return Response({
                "ok": True,
                "message": "Empresa registrada y suscripción activada exitosamente",
                "empresa": {
                    "id": empresa.id,
                    "nombre": empresa.nombre,
                    "subdomain": empresa.subdomain,
                    "activo": empresa.activo,
                    "fecha_creacion": empresa.fecha_creacion.isoformat() if empresa.fecha_creacion else None,
                    "stripe_customer_id": empresa.stripe_customer_id,
                    "stripe_subscription_id": empresa.stripe_subscription_id
                },
                "admin": {
                    "codigo": usuario_admin.codigo,
                    "nombre": usuario_admin.nombre,
                    "apellido": usuario_admin.apellido,
                    "email": usuario_admin.correoelectronico
                },
                "subscription": {
                    "id": subscription.id,
                    "status": subscription.get('status', 'active'),
                    "next_billing_date": next_billing_date,
                    "plan_amount": settings.STRIPE_PRICE_AMOUNT,
                    "trial_days": 14
                },
                "url_acceso": url_acceso,
                "password_temporal": password_temporal,
                "email_enviado": email_enviado,
                "instrucciones": "Tu pago ha sido procesado exitosamente. Revisa tu correo electrónico para las credenciales de acceso."
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Log del error completo para debugging
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error completo al registrar empresa: {error_traceback}")

        return Response({
            "ok": False,
            "message": "Error al registrar la empresa",
            "error": str(e),
            "error_type": type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """
    Webhook para recibir eventos de Stripe (pagos, suscripciones, etc.)

    POST /api/public/stripe-webhook/
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return Response({"error": "Invalid payload"}, status=400)
    except stripe.SignatureVerificationError:
        return Response({"error": "Invalid signature"}, status=400)

    # Manejar diferentes tipos de eventos
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Aquí puedes actualizar el estado de la empresa si es necesario
        print(f"Payment succeeded: {payment_intent['id']}")

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Desactivar empresa cuando se cancela la suscripción
        try:
            empresa = Empresa.objects.get(stripe_subscription_id=subscription['id'])
            empresa.activo = False
            empresa.save()
            print(f"Suscripción cancelada para empresa: {empresa.nombre}")
        except Empresa.DoesNotExist:
            pass

    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        # Notificar al cliente que el pago falló
        print(f"Payment failed: {invoice['id']}")

    return Response({"status": "success"}, status=200)