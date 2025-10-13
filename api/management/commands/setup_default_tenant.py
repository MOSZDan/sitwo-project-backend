from django.core.management.base import BaseCommand
from api.models import Empresa, Usuario

class Command(BaseCommand):
    help = 'Configura el tenant por defecto y lo asigna a usuarios existentes'

    def handle(self, *args, **kwargs):
        # Crear empresa por defecto si no existe
        empresa, created = Empresa.objects.get_or_create(
            nombre='Clínica Dental Principal',
            defaults={
                'subdomain': 'principal',
                'activo': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Empresa creada: {empresa}'))
        else:
            self.stdout.write(f'Empresa existente: {empresa}')

        # Asignar empresa a usuarios que no tienen una
        usuarios_sin_empresa = Usuario.objects.filter(empresa__isnull=True)
        count = usuarios_sin_empresa.update(empresa=empresa)

        self.stdout.write(self.style.SUCCESS(
            f'Se asignó la empresa a {count} usuarios'
        ))