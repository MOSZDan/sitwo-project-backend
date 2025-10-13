from django.db import models
from decimal import Decimal


class PoliticaNoShow(models.Model):
    nombre = models.CharField(max_length=100, null=True, blank=True)
    empresa = models.ForeignKey('api.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    # Estado objetivo de la consulta que dispara la política
    estado_consulta = models.ForeignKey('api.Estadodeconsulta', on_delete=models.CASCADE)

    # Acciones de la política
    penalizacion_economica = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    bloqueo_temporal = models.BooleanField(default=False)
    reprogramacion_obligatoria = models.BooleanField(default=False)
    alerta_interna = models.BooleanField(default=False)
    notificacion_paciente = models.BooleanField(default=False)
    notificacion_profesional = models.BooleanField(default=False)

    # Días de bloqueo si bloqueo_temporal=True
    dias_bloqueo = models.PositiveIntegerField(null=True, blank=True)

    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre or f"Política #{self.pk}"


class Multa(models.Model):
    ESTADO_CHOICES = (
        ("pendiente", "Pendiente"),
        ("pagada", "Pagada"),
        ("anulada", "Anulada"),
    )

    empresa = models.ForeignKey('api.Empresa', on_delete=models.CASCADE, related_name='multas')
    # Ajusta si tu modelo de dominio del usuario tiene otro nombre
    usuario = models.ForeignKey('api.Usuario', on_delete=models.CASCADE, related_name='multas')
    # Ajusta si tu modelo se llama distinto o está en otro app
    consulta = models.ForeignKey('api.Consulta', on_delete=models.CASCADE, related_name='multas')
    politica = models.ForeignKey('no_show_policies.PoliticaNoShow', on_delete=models.SET_NULL, null=True, blank=True, related_name='multas_aplicadas')

    monto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    motivo = models.CharField(max_length=255, blank=True, default="")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    vencimiento = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # Evita duplicar multa por la misma consulta/política
            models.UniqueConstraint(
                fields=["consulta", "politica"],
                name="uniq_multa_por_consulta_y_politica",
            )
        ]
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Multa #{self.pk} - Usuario {self.usuario_id} - {self.estado} - {self.monto}"