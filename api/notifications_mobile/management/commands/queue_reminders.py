from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from api.notifications_mobile.models import ConsultaMN, HorarioMN, UsuarioMN
from api.notifications_mobile.queue import enqueue_notif_for_user_devices

def combine_dt(fecha, hora):
    naive = datetime.combine(fecha, hora)
    return timezone.make_aware(naive, timezone.get_current_timezone())

class Command(BaseCommand):
    help = "Encola recordatorios H24 / H2 por dispositivo del paciente."

    def add_arguments(self, parser):
        parser.add_argument("--tolerance-min", type=int, default=5)
        parser.add_argument("--only", choices=["H24","H2","ALL"], default="ALL")

    def handle(self, *args, **opts):
        tol = timedelta(minutes=opts["tolerance_min"])
        now = timezone.localtime()
        target_h24 = now + timedelta(hours=24)
        target_h2 = now + timedelta(hours=2)

        windows = []
        if opts["only"] in ("ALL","H24"):
            windows.append(("REMINDER_H24", target_h24 - tol, target_h24 + tol))
        if opts["only"] in ("ALL","H2"):
            windows.append(("REMINDER_H2", target_h2 - tol, target_h2 + tol))

        total = 0
        for tipo_nombre, win_start, win_end in windows:
            fechas = {win_start.date(), win_end.date()}
            qs = ConsultaMN.objects.filter(fecha__in=list(fechas))

            cnt = 0
            for c in qs:
                try:
                    h = HorarioMN.objects.get(id=c.idhorario)
                except HorarioMN.DoesNotExist:
                    continue

                appt_dt = combine_dt(c.fecha, h.hora)
                if not (win_start <= appt_dt <= win_end):
                    continue

                try:
                    u = UsuarioMN.objects.get(codigo=c.codpaciente)
                except UsuarioMN.DoesNotExist:
                    continue
                if not (u.recibir_notificaciones and u.notificaciones_push):
                    continue

                titulo = "Recordatorio de consulta"
                mensaje = f"Tienes una consulta el {appt_dt.strftime('%d/%m %H:%M')}"
                data = {
                    "tipo": tipo_nombre,
                    "consulta_id": c.id,
                    "fecha": c.fecha.isoformat(),
                    "hora": h.hora.strftime("%H:%M:%S"),
                }

                rows = enqueue_notif_for_user_devices(
                    usuario_codigo=u.codigo,
                    titulo=titulo,
                    mensaje=mensaje,
                    tipo_nombre=tipo_nombre,
                    data=data,
                )
                cnt += len(rows)

            self.stdout.write(f"{tipo_nombre}: encoladas {cnt}")
            total += cnt

        self.stdout.write(self.style.SUCCESS(f"Total encoladas: {total}"))
