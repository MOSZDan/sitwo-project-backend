from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.notifications_mobile.models import (
    HistorialNotificacionMN,
    UsuarioMN,
    DispositivoMovilMN,
)
from api.notifications_mobile.utils import mobile_send_push_fcm

class Command(BaseCommand):
    help = "Procesa notificaciones PENDING y las envía por FCM."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        limit = opts["limit"]
        dry_run = opts["dry_run"]

        qs = HistorialNotificacionMN.objects.filter(estado="PENDING").order_by("id")[:limit]
        if not qs:
            self.stdout.write(self.style.WARNING("No hay PENDING"))
            return

        processed = 0
        for h in qs:
            with transaction.atomic():
                h = (HistorialNotificacionMN.objects
                     .select_for_update(skip_locked=True)
                     .get(id=h.id))

                if h.estado != "PENDING":
                    continue

                try:
                    u = UsuarioMN.objects.get(codigo=h.codusuario)
                except UsuarioMN.DoesNotExist:
                    h.estado = "ERROR"
                    h.error_mensaje = "Usuario inexistente"
                    h.intentos = (h.intentos or 0) + 1
                    h.fecha_envio = timezone.now()
                    h.save()
                    continue

                if not (u.recibir_notificaciones and u.notificaciones_push):
                    h.estado = "SKIPPED_PREF"
                    h.intentos = (h.intentos or 0) + 1
                    h.fecha_envio = timezone.now()
                    h.save()
                    processed += 1
                    continue

                tokens = []
                if h.iddispositivomovil:
                    d = DispositivoMovilMN.objects.filter(
                        id=h.iddispositivomovil, codusuario=u.codigo, activo=True
                    ).first()
                    if d:
                        tokens = [d.token_fcm]
                else:
                    tokens = list(
                        DispositivoMovilMN.objects
                        .filter(codusuario=u.codigo, activo=True)
                        .values_list("token_fcm", flat=True)
                    )

                now = timezone.now()
                if not tokens:
                    h.estado = "NO_TOKENS"
                    h.error_mensaje = "No hay dispositivos activos"
                    h.intentos = (h.intentos or 0) + 1
                    h.fecha_envio = now
                    h.save()
                    processed += 1
                    continue

                if dry_run:
                    self.stdout.write(f"DRY-RUN id={h.id} tokens={len(tokens)}")
                    continue

                res = mobile_send_push_fcm(
                    tokens=tokens,
                    title=h.titulo,
                    body=h.mensaje,
                    data=h.datos_adicionales or {},
                    android_channel_id="smilestudio_default",
                )
                sent = int(res.get("sent", 0))
                estado = "SENT" if sent == len(tokens) else ("PARTIAL" if sent > 0 else "ERROR")

                h.estado = estado
                h.intentos = (h.intentos or 0) + 1
                h.fecha_envio = now
                if res.get("errors"):
                    h.error_mensaje = "\n".join(res["errors"])[:1000]
                h.save()

                self.stdout.write(f"{estado} id={h.id} sent={sent}/{len(tokens)}")
                processed += 1

        self.stdout.write(self.style.SUCCESS(f"Procesadas: {processed}"))
