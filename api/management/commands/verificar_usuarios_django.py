from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from api.models import Usuario


class Command(BaseCommand):
    help = 'Verificar y corregir usuarios de autenticación de Django'

    def handle(self, *args, **options):
        # Buscar el usuario de Django relacionado con el Dr. Juan Pérez
        try:
            # Buscar el usuario en la tabla api_usuario
            usuario_api = Usuario.objects.get(codigo=132)
            
            # Verificar si hay un usuario de Django con el mismo correo
            user_django = User.objects.filter(email=usuario_api.correoelectronico).first()
            
            if user_django:
                self.stdout.write(f'Usuario Django encontrado: {user_django.username} (ID: {user_django.id})')
                self.stdout.write(f'Email: {user_django.email}')
                
                # Actualizar la contraseña del usuario de Django también
                nueva_contrasena = 'dentista123'
                user_django.password = make_password(nueva_contrasena)
                user_django.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Contraseña actualizada para el usuario Django: {user_django.username}')
                )
                self.stdout.write(f'Nueva contraseña temporal: {nueva_contrasena}')
            else:
                # Crear un usuario de Django si no existe
                username = f"juanperez_{usuario_api.codigo}"
                nueva_contrasena = 'dentista123'
                
                user_django = User.objects.create_user(
                    username=username,
                    email=usuario_api.correoelectronico,
                    password=nueva_contrasena,
                    first_name=usuario_api.nombre,
                    last_name=usuario_api.apellido
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Usuario Django creado: {user_django.username} (ID: {user_django.id})')
                )
                self.stdout.write(f'Email: {user_django.email}')
                self.stdout.write(f'Contraseña temporal: {nueva_contrasena}')
        
        except Usuario.DoesNotExist:
            self.stdout.write('No se encontró el usuario con ID 132')
        
        # Mostrar todos los usuarios de Django
        self.stdout.write('\nUsuarios de Django existentes:')
        for user in User.objects.all():
            self.stdout.write(f'  - Username: {user.username}, Email: {user.email}, ID: {user.id}')