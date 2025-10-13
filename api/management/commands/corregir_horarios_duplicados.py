from django.core.management.base import BaseCommand
from api.models import Empresa, Horario


class Command(BaseCommand):
    help = 'Corregir horarios duplicados y asociarlos a la Clínica Dental Sur'

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
            self.stdout.write(f'Buscando hora {hora}: Encontrados {horarios_con_hora.count()} registros')
            
            if horarios_con_hora.count() > 0:
                # Agrupar por empresa
                horarios_por_empresa = {}
                for horario in horarios_con_hora:
                    empresa_id = horario.empresa.id if horario.empresa else None
                    if empresa_id not in horarios_por_empresa:
                        horarios_por_empresa[empresa_id] = []
                    horarios_por_empresa[empresa_id].append(horario)
                
                for emp_id, lista_horarios in horarios_por_empresa.items():
                    empresa_nombre = "NINGUNA" if emp_id is None else next((e.nombre for e in Empresa.objects.all() if e.id == emp_id), f"ID:{emp_id}")
                    self.stdout.write(f'  - Empresa {empresa_nombre} ({emp_id}): {len(lista_horarios)} registros')
                    
                    if emp_id == empresa.id:
                        # Si ya están en la empresa correcta, solo asegurarse de que sea un único registro
                        if len(lista_horarios) > 1:
                            # Mantener solo uno y eliminar los demás
                            for horario in lista_horarios[1:]:
                                self.stdout.write(f'    -> Eliminando duplicado ID: {horario.id}')
                                horario.delete()
                    else:
                        # Si están en otra empresa, moverlos a la empresa correcta
                        for horario in lista_horarios:
                            # Verificar si ya existe un horario para esta hora y empresa
                            existe = Horario.objects.filter(hora=hora, empresa=empresa).exists()
                            if not existe:
                                horario.empresa = empresa
                                horario.save()
                                self.stdout.write(f'    -> Asignando ID: {horario.id} a {empresa.nombre}')
                            else:
                                # Si ya existe un horario para esta hora y empresa, eliminar este duplicado
                                self.stdout.write(f'    -> Eliminando duplicado ID: {horario.id} (ya existe otro para esta empresa)')
                                horario.delete()
        
        # Contar horarios totales asociados a Clínica Dental Sur
        horarios_empresa = Horario.objects.filter(empresa=empresa)
        self.stdout.write(
            self.style.SUCCESS(f'Total de horarios ahora asociados a {empresa.nombre}: {horarios_empresa.count()}')
        )
        
        # Mostrar los horarios actuales
        self.stdout.write('Horarios actuales para la empresa:')
        for horario in horarios_empresa:
            self.stdout.write(f'  - {horario.hora} (ID: {horario.id})')