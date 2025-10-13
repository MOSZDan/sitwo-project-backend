from django.core.management.base import BaseCommand
from api.models import Empresa, Horario


class Command(BaseCommand):
    help = 'Corregir horarios y asociarlos a la Clínica Dental Sur'

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

        # Verificar horarios existentes
        from datetime import time
        
        horarios_basicos = [
            time(8, 0), time(9, 0), time(10, 0), time(11, 0), 
            time(12, 0), time(14, 0), time(15, 0), time(16, 0), 
            time(17, 0), time(18, 0)
        ]
        
        for hora in horarios_basicos:
            # Buscar horarios con esta hora específica
            horarios_con_hora = Horario.objects.filter(hora=hora)
            self.stdout.write(f'Horas {hora}: Encontrados {horarios_con_hora.count()} registros')
            
            for horario in horarios_con_hora:
                self.stdout.write(f'  - ID: {horario.id}, Empresa: {horario.empresa.nombre if horario.empresa else "NINGUNA"}')
                
                # Si el horario no pertenece a Clínica Dental Sur, cambiarlo
                if horario.empresa != empresa:
                    horario.empresa = empresa
                    horario.save()
                    self.stdout.write(f'    -> Asignado a {empresa.nombre}')
        
        # Contar horarios totales asociados a Clínica Dental Sur
        horarios_empresa = Horario.objects.filter(empresa=empresa)
        self.stdout.write(
            self.style.SUCCESS(f'Total de horarios ahora asociados a {empresa.nombre}: {horarios_empresa.count()}')
        )