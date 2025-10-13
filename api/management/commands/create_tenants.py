# api/management/commands/create_tenants.py
from django.core.management.base import BaseCommand
from api.models import Empresa


class Command(BaseCommand):
    help = 'Crea empresas de ejemplo para multi-tenancy'

    def handle(self, *args, **options):
        empresas_data = [
            {
                'nombre': 'Clínica Dental Norte',
                'subdomain': 'norte',
                'activo': True
            },
            {
                'nombre': 'Clínica Dental Sur',
                'subdomain': 'sur',
                'activo': True
            },
            {
                'nombre': 'Clínica Dental Este',
                'subdomain': 'este',
                'activo': True
            },
            {
                'nombre': 'Clínica Dental Oeste',
                'subdomain': 'oeste',
                'activo': True
            },
        ]

        self.stdout.write(self.style.WARNING('Creando empresas para multi-tenancy...'))

        created_count = 0
        updated_count = 0

        for empresa_data in empresas_data:
            empresa, created = Empresa.objects.get_or_create(
                subdomain=empresa_data['subdomain'],
                defaults={
                    'nombre': empresa_data['nombre'],
                    'activo': empresa_data['activo']
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'[+] Empresa creada: {empresa.nombre} ({empresa.subdomain})')
                )
            else:
                # Actualizar si ya existe
                empresa.nombre = empresa_data['nombre']
                empresa.activo = empresa_data['activo']
                empresa.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'[*] Empresa actualizada: {empresa.nombre} ({empresa.subdomain})')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nProceso completado: {created_count} creadas, {updated_count} actualizadas'
            )
        )

        # Mostrar todas las empresas actuales
        self.stdout.write(self.style.WARNING('\nEmpresas disponibles:'))
        for empresa in Empresa.objects.all():
            status = 'activa' if empresa.activo else 'inactiva'
            self.stdout.write(f'  - {empresa.nombre} ({empresa.subdomain}) - {status}')
