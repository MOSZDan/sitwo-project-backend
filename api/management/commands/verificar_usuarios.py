from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from api.models import Usuario


class Command(BaseCommand):
    help = 'Verificar y crear credenciales para odontólogos'

    def handle(self, *args, **options):
        # Buscar al Dr. Juan Pérez
        try:
            usuario = Usuario.objects.get(codigo=132)
            self.stdout.write(f'Usuario encontrado: {usuario.nombre} {usuario.apellido}')
            self.stdout.write(f'Email: {usuario.correoelectronico}')
            self.stdout.write(f'ID: {usuario.codigo}')
            
            # Mostrar la contraseña actual (hash)
            # self.stdout.write(f'Contraseña hash: {usuario.password}')
            
            # Crear una contraseña temporal para el usuario
            nueva_contrasena = 'dentista123'  # Contraseña temporal fácil de recordar
            usuario.password = make_password(nueva_contrasena)
            usuario.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Contraseña actualizada para {usuario.nombre} {usuario.apellido}')
            )
            self.stdout.write(f'Nueva contraseña temporal: {nueva_contrasena}')
            
        except Usuario.DoesNotExist:
            self.stdout.write('No se encontró el usuario con ID 132')
            
        # Mostrar todos los usuarios odontólogos de la Clínica Dental Sur
        self.stdout.write('\nOtros usuarios odontólogos de Clínica Dental Sur:')
        odontologos = Usuario.objects.filter(
            idtipousuario__rol='Odontólogo'
        ).filter(
            odontologo__empresa__subdomain='clinicasur'
        ).select_related('idtipousuario', 'odontologo')
        
        for usuario in odontologos:
            self.stdout.write(f'  - {usuario.nombre} {usuario.apellido}')
            self.stdout.write(f'    ID: {usuario.codigo}')
            self.stdout.write(f'    Email: {usuario.correoelectronico}')
            if hasattr(usuario, 'odontologo') and usuario.odontologo.especialidad:
                self.stdout.write(f'    Especialidad: {usuario.odontologo.especialidad}')
            self.stdout.write('')