from django.core.management.base import BaseCommand
from api.models import Empresa, Horario


class Command(BaseCommand):
    help = 'Verificación específica de horarios por empresa'

    def handle(self, *args, **options):
        # Buscar la empresa Clínica Dental Sur
        try:
            empresa = Empresa.objects.get(subdomain='clinicasur')
            self.stdout.write(
                self.style.SUCCESS(f'Empresa encontrada: {empresa.nombre} (ID: {empresa.id})')
            )
        except Empresa.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('No se encontró la empresa Clínica Dental Sur')
            )
            return

        # Contar horarios asociados a esta empresa
        horarios_empresa = Horario.objects.filter(empresa=empresa)
        self.stdout.write(f'Total de horarios con empresa asignada: {horarios_empresa.count()}')
        
        # Mostrar los horarios existentes para esta empresa
        for horario in horarios_empresa:
            self.stdout.write(f'  - Horario: {horario.hora} (ID: {horario.id})')

        # Contar horarios sin empresa
        horarios_sin_empresa = Horario.objects.filter(empresa__isnull=True)
        self.stdout.write(f'Total de horarios sin empresa: {horarios_sin_empresa.count()}')
        
        # Mostrar horarios sin empresa
        for horario in horarios_sin_empresa:
            self.stdout.write(f'  - Horario sin empresa: {horario.hora} (ID: {horario.id})')
        
        # Crear horarios básicos si no existen para la empresa
        if horarios_empresa.count() == 0:
            from datetime import time
            
            horarios_basicos = [
                time(8, 0), time(9, 0), time(10, 0), time(11, 0), 
                time(12, 0), time(14, 0), time(15, 0), time(16, 0), 
                time(17, 0), time(18, 0)
            ]
            
            creados = 0
            for hora in horarios_basicos:
                # Buscar si ya existe un horario con esta hora
                horario_existente = Horario.objects.filter(hora=hora).first()
                if horario_existente:
                    # Si existe pero no tiene empresa, asignársela
                    if horario_existente.empresa is None:
                        horario_existente.empresa = empresa
                        horario_existente.save()
                        creados += 1
                else:
                    # Si no existe, crearlo
                    Horario.objects.create(
                        hora=hora,
                        empresa=empresa
                    )
                    creados += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Creados/asignados {creados} horarios básicos para la empresa {empresa.nombre}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Ya existen {horarios_empresa.count()} horarios para la empresa')
            )