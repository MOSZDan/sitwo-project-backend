from django.core.management.base import BaseCommand
from api.models import Empresa, Odontologo, Horario, Tipodeconsulta, Usuario, Paciente
from django.db import transaction


class Command(BaseCommand):
    help = 'Diagnóstico de datos de la Clínica Dental Sur'

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

        # Contar odontólogos asociados a esta empresa
        odontologos_count = Odontologo.objects.filter(empresa=empresa).count()
        self.stdout.write(f'Odontólogos asociados a la empresa: {odontologos_count}')
        
        if odontologos_count > 0:
            odontologos = Odontologo.objects.filter(empresa=empresa).select_related('codusuario')
            for odontologo in odontologos:
                self.stdout.write(f'  - Odontólogo: {odontologo.codusuario.nombre} {odontologo.codusuario.apellido} (ID: {odontologo.codusuario.codigo})')

        # Contar horarios asociados a esta empresa
        horarios_count = Horario.objects.filter(empresa=empresa).count()
        self.stdout.write(f'Horarios asociados a la empresa: {horarios_count}')
        
        if horarios_count > 0:
            horarios = Horario.objects.filter(empresa=empresa)
            for horario in horarios:
                self.stdout.write(f'  - Horario: {horario.hora} (ID: {horario.id})')

        # Contar tipos de consulta asociados a esta empresa
        tipos_consulta_count = Tipodeconsulta.objects.filter(empresa=empresa).count()
        self.stdout.write(f'Tipos de consulta asociados a la empresa: {tipos_consulta_count}')
        
        if tipos_consulta_count > 0:
            tipos = Tipodeconsulta.objects.filter(empresa=empresa)
            for tipo in tipos:
                self.stdout.write(f'  - Tipo de consulta: {tipo.nombreconsulta} (ID: {tipo.id})')

        # Contar usuarios y pacientes asociados a esta empresa
        usuarios_count = Usuario.objects.filter(empresa=empresa).count()
        self.stdout.write(f'Usuarios asociados a la empresa: {usuarios_count}')
        
        pacientes_count = Paciente.objects.filter(empresa=empresa).count()
        self.stdout.write(f'Pacientes asociados a la empresa: {pacientes_count}')

        # Verificar si hay odontólogos con usuarios asociados
        odontologos_con_usuarios = Odontologo.objects.filter(empresa=empresa).select_related('codusuario')
        self.stdout.write(f'Odontólogos con usuarios asociados: {odontologos_con_usuarios.count()}')
        
        for odontologo in odontologos_con_usuarios:
            self.stdout.write(f'  - {odontologo.codusuario.nombre} {odontologo.codusuario.apellido} (Rol: {odontologo.codusuario.idtipousuario.rol if odontologo.codusuario.idtipousuario else "Sin rol"})')

        # Verificar si hay horarios sin empresa que podrían ser migrados
        horarios_sin_empresa = Horario.objects.filter(empresa__isnull=True)
        self.stdout.write(f'Horarios sin empresa: {horarios_sin_empresa.count()}')

        # Verificar si hay tipos de consulta sin empresa que podrían ser migrados
        tipos_sin_empresa = Tipodeconsulta.objects.filter(empresa__isnull=True)
        self.stdout.write(f'Tipos de consulta sin empresa: {tipos_sin_empresa.count()}')

        # Verificar si hay odontólogos sin empresa que podrían ser migrados
        odontologos_sin_empresa = Odontologo.objects.filter(empresa__isnull=True)
        self.stdout.write(f'Odontólogos sin empresa: {odontologos_sin_empresa.count()}')