from django.core.management.base import BaseCommand
from django.db import transaction
from api.models_notifications import TipoNotificacion, CanalNotificacion, PlantillaNotificacion


class Command(BaseCommand):
    help = 'Inicializa el sistema de notificaciones con datos por defecto'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-templates',
            action='store_true',
            help='Crear también plantillas por defecto',
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Inicializando sistema de notificaciones...')

            # Crear tipos de notificación
            tipos_creados = self.crear_tipos_notificacion()

            # Crear canales de notificación
            canales_creados = self.crear_canales_notificacion()

            # Crear plantillas si se solicita
            plantillas_creadas = 0
            if options['with_templates']:
                plantillas_creadas = self.crear_plantillas_default()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Sistema de notificaciones inicializado correctamente:\n'
                    f'- Tipos de notificación creados: {tipos_creados}\n'
                    f'- Canales creados: {canales_creados}\n'
                    f'- Plantillas creadas: {plantillas_creadas}'
                )
            )

    def crear_tipos_notificacion(self):
        tipos_default = [
            {
                'nombre': 'Recordatorio de Cita',
                'descripcion': 'Recordatorio enviado antes de una cita programada'
            },
            {
                'nombre': 'Confirmación de Cita',
                'descripcion': 'Confirmación cuando se agenda una nueva cita'
            },
            {
                'nombre': 'Cancelación de Cita',
                'descripcion': 'Notificación cuando se cancela una cita'
            },
            {
                'nombre': 'Reagendamiento de Cita',
                'descripcion': 'Notificación cuando se reagenda una cita'
            },
            {
                'nombre': 'Resultado Disponible',
                'descripcion': 'Notificación cuando están disponibles resultados de estudios'
            },
            {
                'nombre': 'Factura Generada',
                'descripcion': 'Notificación cuando se genera una nueva factura'
            },
            {
                'nombre': 'Pago Confirmado',
                'descripcion': 'Confirmación cuando se recibe un pago'
            },
            {
                'nombre': 'Pago Vencido',
                'descripcion': 'Notificación cuando un pago está vencido'
            },
            {
                'nombre': 'Plan de Tratamiento',
                'descripcion': 'Notificaciones relacionadas con planes de tratamiento'
            },
            {
                'nombre': 'Sistema',
                'descripcion': 'Notificaciones generales del sistema'
            },
            {
                'nombre': 'Promociones',
                'descripcion': 'Ofertas y promociones especiales'
            }
        ]

        creados = 0
        for tipo_data in tipos_default:
            tipo, created = TipoNotificacion.objects.get_or_create(
                nombre=tipo_data['nombre'],
                defaults={'descripcion': tipo_data['descripcion']}
            )
            if created:
                creados += 1
                self.stdout.write(f'  ✓ Tipo creado: {tipo.nombre}')
            else:
                self.stdout.write(f'  - Tipo ya existe: {tipo.nombre}')

        return creados

    def crear_canales_notificacion(self):
        canales_default = [
            {
                'nombre': 'email',
                'descripcion': 'Notificaciones por correo electrónico'
            },
            {
                'nombre': 'push',
                'descripcion': 'Notificaciones push para dispositivos móviles'
            },
            {
                'nombre': 'sms',
                'descripcion': 'Notificaciones por SMS'
            },
            {
                'nombre': 'whatsapp',
                'descripcion': 'Notificaciones por WhatsApp'
            }
        ]

        creados = 0
        for canal_data in canales_default:
            canal, created = CanalNotificacion.objects.get_or_create(
                nombre=canal_data['nombre'],
                defaults={'descripcion': canal_data['descripcion']}
            )
            if created:
                creados += 1
                self.stdout.write(f'  ✓ Canal creado: {canal.get_nombre_display()}')
            else:
                self.stdout.write(f'  - Canal ya existe: {canal.get_nombre_display()}')

        return creados

    def crear_plantillas_default(self):
        plantillas_data = [
            # Recordatorio de Cita - Email
            {
                'tipo': 'Recordatorio de Cita',
                'canal': 'email',
                'nombre': 'Recordatorio de Cita - Email',
                'asunto': 'Recordatorio: Cita dental mañana',
                'titulo': 'Recordatorio de Cita',
                'mensaje': '''Hola {{nombre}},

Te recordamos que tienes una cita programada para mañana {{fecha}} a las {{hora}}.

Detalles de la cita:
- Tipo: {{tipo_consulta}}
- Doctor: {{doctor}}
- Ubicación: {{ubicacion}}

Si necesitas cancelar o reagendar, por favor contáctanos al menos 24 horas antes.

¡Te esperamos!''',
                'variables': ['nombre', 'fecha', 'hora', 'tipo_consulta', 'doctor', 'ubicacion']
            },

            # Recordatorio de Cita - Push
            {
                'tipo': 'Recordatorio de Cita',
                'canal': 'push',
                'nombre': 'Recordatorio de Cita - Push',
                'asunto': '',
                'titulo': 'Cita mañana a las {{hora}}',
                'mensaje': 'Hola {{nombre}}, te recordamos tu cita dental programada para mañana.',
                'variables': ['nombre', 'hora']
            },

            # Confirmación de Cita - Email
            {
                'tipo': 'Confirmación de Cita',
                'canal': 'email',
                'nombre': 'Confirmación de Cita - Email',
                'asunto': '✓ Cita confirmada - {{fecha}}',
                'titulo': 'Cita Confirmada',
                'mensaje': '''¡Hola {{nombre}}!

Tu cita ha sido confirmada exitosamente:

📅 Fecha: {{fecha}}
🕐 Hora: {{hora}}
👨‍⚕️ Doctor: {{doctor}}
🏥 Tipo: {{tipo_consulta}}

Recomendaciones antes de tu cita:
- Llega 15 minutos antes
- Trae tu documento de identidad
- Si tomas medicamentos, informa al doctor

¡Nos vemos pronto!''',
                'variables': ['nombre', 'fecha', 'hora', 'doctor', 'tipo_consulta']
            },

            # Confirmación de Cita - Push
            {
                'tipo': 'Confirmación de Cita',
                'canal': 'push',
                'nombre': 'Confirmación de Cita - Push',
                'asunto': '',
                'titulo': '✓ Cita confirmada',
                'mensaje': 'Tu cita para el {{fecha}} a las {{hora}} ha sido confirmada.',
                'variables': ['fecha', 'hora']
            },

            # Factura Generada - Email
            {
                'tipo': 'Factura Generada',
                'canal': 'email',
                'nombre': 'Factura Generada - Email',
                'asunto': 'Nueva factura generada #{{numero_factura}}',
                'titulo': 'Factura Generada',
                'mensaje': '''Hola {{nombre}},

Se ha generado una nueva factura por los servicios recibidos:

🧾 Número de factura: {{numero_factura}}
💰 Monto total: ${{monto_total}}
📅 Fecha de emisión: {{fecha_emision}}
📋 Servicios: {{servicios}}

Puedes realizar el pago a través de:
- Efectivo en la clínica
- Transferencia bancaria
- Tarjeta de crédito/débito

¡Gracias por confiar en nosotros!''',
                'variables': ['nombre', 'numero_factura', 'monto_total', 'fecha_emision', 'servicios']
            },

            # Pago Confirmado - Email
            {
                'tipo': 'Pago Confirmado',
                'canal': 'email',
                'nombre': 'Pago Confirmado - Email',
                'asunto': '✓ Pago recibido - Factura #{{numero_factura}}',
                'titulo': 'Pago Confirmado',
                'mensaje': '''¡Hola {{nombre}}!

Confirmamos que hemos recibido tu pago:

✅ Factura: #{{numero_factura}}
💵 Monto pagado: ${{monto_pagado}}
📅 Fecha de pago: {{fecha_pago}}
💳 Método: {{metodo_pago}}

Tu recibo está disponible en tu perfil.

¡Gracias por tu pago puntual!''',
                'variables': ['nombre', 'numero_factura', 'monto_pagado', 'fecha_pago', 'metodo_pago']
            },
        ]

        creados = 0
        for plantilla_data in plantillas_data:
            try:
                tipo = TipoNotificacion.objects.get(nombre=plantilla_data['tipo'])
                canal = CanalNotificacion.objects.get(nombre=plantilla_data['canal'])

                plantilla, created = PlantillaNotificacion.objects.get_or_create(
                    tipo_notificacion=tipo,
                    canal_notificacion=canal,
                    defaults={
                        'nombre': plantilla_data['nombre'],
                        'asunto_template': plantilla_data['asunto'],
                        'titulo_template': plantilla_data['titulo'],
                        'mensaje_template': plantilla_data['mensaje'],
                        'variables_disponibles': plantilla_data['variables']
                    }
                )

                if created:
                    creados += 1
                    self.stdout.write(f'  ✓ Plantilla creada: {plantilla.nombre}')
                else:
                    self.stdout.write(f'  - Plantilla ya existe: {plantilla.nombre}')

            except (TipoNotificacion.DoesNotExist, CanalNotificacion.DoesNotExist) as e:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Error creando plantilla {plantilla_data["nombre"]}: {e}')
                )

        return creados