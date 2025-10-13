from django.core.management.base import BaseCommand
from api.models import Usuario, Odontologo


class Command(BaseCommand):
    help = 'Verificar credenciales de odontólogos'

    def handle(self, *args, **options):
        # Buscar odontólogos con sus usuarios
        odontologos = Odontologo.objects.select_related('codusuario').all()
        
        self.stdout.write('Odontólogos encontrados:')
        for odontologo in odontologos:
            usuario = odontologo.codusuario
            self.stdout.write(f'  - {usuario.nombre} {usuario.apellido} (ID: {usuario.codigo})')
            self.stdout.write(f'    Email: {usuario.correoelectronico}')
            self.stdout.write(f'    Rol: {usuario.idtipousuario.rol}')
            if hasattr(odontologo, 'especialidad') and odontologo.especialidad:
                self.stdout.write(f'    Especialidad: {odontologo.especialidad}')
            self.stdout.write('')
        
        # Buscar específicamente al Dr. Juan Pérez
        self.stdout.write('Buscando Dr. Juan Pérez:')
        juan_perez = Odontologo.objects.filter(
            codusuario__nombre='Juan',
            codusuario__apellido='Pérez'
        ).select_related('codusuario').first()
        
        if juan_perez:
            usuario = juan_perez.codusuario
            self.stdout.write(f'  - Nombre: {usuario.nombre} {usuario.apellido}')
            self.stdout.write(f'    ID: {usuario.codigo}')
            self.stdout.write(f'    Email: {usuario.correoelectronico}')
            self.stdout.write(f'    Rol: {usuario.idtipousuario.rol}')
            if juan_perez.especialidad:
                self.stdout.write(f'    Especialidad: {juan_perez.especialidad}')
        else:
            self.stdout.write('  - No se encontró al Dr. Juan Pérez')
        
        # Buscar otros usuarios que podrían ser el Dr. Juan Pérez
        usuarios_similares = Usuario.objects.filter(
            nombre__icontains='juan'
        )
        self.stdout.write('\nOtros usuarios con nombre similar a "Juan":')
        for usuario in usuarios_similares:
            self.stdout.write(f'  - {usuario.nombre} {usuario.apellido} (ID: {usuario.codigo}) - Email: {usuario.correoelectronico}')