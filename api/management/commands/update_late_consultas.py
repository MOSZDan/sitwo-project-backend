from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Consulta, Estadodeconsulta, Horario

class Command(BaseCommand):
    help = 'Marca las consultas como atrasadas si ya pasó la fecha y hora y siguen pendientes'

    def handle(self, *args, **options):
        now = timezone.now()

        # Buscar el estado "Pendiente" y "Atrasado"
        try:
            estado_pendiente = Estadodeconsulta.objects.get(estado__iexact='En Hora')
            estado_atrasado = Estadodeconsulta.objects.get(estado__iexact='Atrasado')
        except Estadodeconsulta.DoesNotExist:
            self.stdout.write(self.style.ERROR("No se encontró algún estado ('Pendiente' o 'Atrasado') en Estadodeconsulta"))
            return

        # Si tienes el horario separado, combínalo con la fecha para obtener el datetime completo
        consultas_pendientes = Consulta.objects.filter(idestadoconsulta=estado_pendiente)

        count = 0
        for consulta in consultas_pendientes:
            # Combinar fecha + hora del horario
            fecha_consulta = consulta.fecha
            hora_consulta = consulta.idhorario.hora  # TimeField

            # Combinar fecha y hora en un solo datetime
            from datetime import datetime, time
            dt_consulta = datetime.combine(fecha_consulta, hora_consulta)
            dt_consulta = timezone.make_aware(dt_consulta, timezone.get_current_timezone())

            if dt_consulta < now:
                consulta.idestadoconsulta = estado_atrasado
                consulta.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f'{count} consultas marcadas como atrasadas'))