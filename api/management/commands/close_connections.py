# api/management/commands/close_connections.py
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = 'Cierra todas las conexiones de base de datos activas'

    def handle(self, *args, **options):
        # Cerrar todas las conexiones de base de datos
        for alias in connections:
            try:
                connections[alias].close()
                self.stdout.write(
                    self.style.SUCCESS(f'Conexión "{alias}" cerrada exitosamente')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error cerrando conexión "{alias}": {e}')
                )

        self.stdout.write(
            self.style.SUCCESS('Todas las conexiones han sido procesadas')
        )
