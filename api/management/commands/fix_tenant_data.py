from django.core.management.base import BaseCommand
from api.models import Empresa, Odontologo, Horario, Tipodeconsulta, Paciente, Usuario, Tipodeusuario
from django.db import transaction


class Command(BaseCommand):
    help = 'Crea la Clínica Dental Sur y asocia datos existentes a esta empresa'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Crear la Clínica Dental Sur
            empresa, created = Empresa.objects.get_or_create(
                subdomain='clinicasur',
                defaults={
                    'nombre': 'Clínica Dental Sur',
                    'activo': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Creada empresa: {empresa.nombre} ({empresa.subdomain})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Empresa ya existía: {empresa.nombre} ({empresa.subdomain})')
                )

            # Asegurar que haya al menos algunos tipos de consulta básicos
            tipos_basicos = ['Control Odontológico', 'Limpieza Dental', 'Extracción', 'Empaste', 'Ortodoncia', 'Endodoncia']
            for tipo_nombre in tipos_basicos:
                # Buscar si ya existe un tipo de consulta con este nombre
                tipo_consulta_existente = Tipodeconsulta.objects.filter(nombreconsulta=tipo_nombre).first()
                if tipo_consulta_existente:
                    # Si existe, asegurar que tenga empresa asociada
                    if tipo_consulta_existente.empresa is None:
                        tipo_consulta_existente.empresa = empresa
                        tipo_consulta_existente.save()
                else:
                    # Si no existe, crearlo
                    tipo_consulta = Tipodeconsulta.objects.create(
                        nombreconsulta=tipo_nombre,
                        empresa=empresa
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Creados/actualizados tipos de consulta básicos')
            )

            # Asegurar que haya algunos horarios básicos
            horarios_basicos = [
                '08:00', '09:00', '10:00', '11:00', '12:00', 
                '14:00', '15:00', '16:00', '17:00', '18:00'
            ]
            for hora_str in horarios_basicos:
                from datetime import time
                hora = time.fromisoformat(f"{hora_str}:00")
                # Buscar si ya existe un horario con esta hora
                horario_existente = Horario.objects.filter(hora=hora).first()
                if horario_existente:
                    # Si existe, asegurar que tenga empresa asociada
                    if horario_existente.empresa is None:
                        horario_existente.empresa = empresa
                        horario_existente.save()
                else:
                    # Si no existe, crearlo
                    horario = Horario.objects.create(
                        hora=hora,
                        empresa=empresa
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Creados/actualizados horarios básicos')
            )

            # Asociar odontólogos sin empresa a la Clínica Dental Sur
            odontologos_sin_empresa = Odontologo.objects.filter(empresa__isnull=True)
            for odontologo in odontologos_sin_empresa:
                odontologo.empresa = empresa
                odontologo.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Asociados {odontologos_sin_empresa.count()} odontólogos a la Clínica Dental Sur')
            )

            # Asociar horarios existentes sin empresa a la Clínica Dental Sur
            horarios_sin_empresa = Horario.objects.filter(empresa__isnull=True)
            for horario in horarios_sin_empresa:
                horario.empresa = empresa
                horario.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Asociados {horarios_sin_empresa.count()} horarios a la Clínica Dental Sur')
            )

            # Asociar tipos de consulta existentes sin empresa a la Clínica Dental Sur
            tipos_sin_empresa = Tipodeconsulta.objects.filter(empresa__isnull=True)
            for tipo in tipos_sin_empresa:
                tipo.empresa = empresa
                tipo.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Asociados {tipos_sin_empresa.count()} tipos de consulta a la Clínica Dental Sur')
            )

            # Asociar pacientes sin empresa a la Clínica Dental Sur
            pacientes_sin_empresa = Paciente.objects.filter(empresa__isnull=True)
            for paciente in pacientes_sin_empresa:
                paciente.empresa = empresa
                paciente.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Asociados {pacientes_sin_empresa.count()} pacientes a la Clínica Dental Sur')
            )

            # Asociar usuarios sin empresa a la Clínica Dental Sur
            usuarios_sin_empresa = Usuario.objects.filter(empresa__isnull=True)
            for usuario in usuarios_sin_empresa:
                usuario.empresa = empresa
                usuario.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Asociados {usuarios_sin_empresa.count()} usuarios a la Clínica Dental Sur')
            )

            # Asociar tipos de usuario sin empresa a la Clínica Dental Sur
            tipos_usuario_sin_empresa = Tipodeusuario.objects.filter(empresa__isnull=True)
            for tipo_usuario in tipos_usuario_sin_empresa:
                tipo_usuario.empresa = empresa
                tipo_usuario.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Asociados {tipos_usuario_sin_empresa.count()} tipos de usuario a la Clínica Dental Sur')
            )

            self.stdout.write(
                self.style.SUCCESS('Proceso completado exitosamente. Todos los datos están ahora asociados a la Clínica Dental Sur.')
            )