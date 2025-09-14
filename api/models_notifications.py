# api/models_notifications.py
from django.db import models
from .models import Usuario


class TipoNotificacion(models.Model):
    """
    Tipos de notificaciones disponibles en el sistema
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tiponotificacion'
        verbose_name = 'Tipo de Notificación'
        verbose_name_plural = 'Tipos de Notificación'

    def __str__(self):
        return self.nombre


class CanalNotificacion(models.Model):
    """
    Canales por los cuales se pueden enviar notificaciones
    """
    CANALES = [
        ('email', 'Correo Electrónico'),
        ('push', 'Notificación Push'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]

    nombre = models.CharField(max_length=50, choices=CANALES, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'canalnotificacion'
        verbose_name = 'Canal de Notificación'
        verbose_name_plural = 'Canales de Notificación'

    def __str__(self):
        return self.get_nombre_display()


class PreferenciaNotificacion(models.Model):
    """
    Preferencias de notificación por usuario
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='codusuario')
    tipo_notificacion = models.ForeignKey(TipoNotificacion, on_delete=models.CASCADE, db_column='idtiponotificacion')
    canal_notificacion = models.ForeignKey(CanalNotificacion, on_delete=models.CASCADE, db_column='idcanalnotificacion')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'preferencianotificacion'
        unique_together = ['usuario', 'tipo_notificacion', 'canal_notificacion']
        verbose_name = 'Preferencia de Notificación'
        verbose_name_plural = 'Preferencias de Notificación'

    def __str__(self):
        return f"{self.usuario.nombre} - {self.tipo_notificacion.nombre} - {self.canal_notificacion.nombre}"


class DispositivoMovil(models.Model):
    """
    Dispositivos móviles registrados para notificaciones push
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='codusuario')
    token_fcm = models.TextField(unique=True)  # Token de Firebase Cloud Messaging
    plataforma = models.CharField(max_length=20, choices=[('android', 'Android'), ('ios', 'iOS')])
    modelo_dispositivo = models.CharField(max_length=100, blank=True, null=True)
    version_app = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_actividad = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dispositivomovil'
        verbose_name = 'Dispositivo Móvil'
        verbose_name_plural = 'Dispositivos Móviles'

    def __str__(self):
        return f"{self.usuario.nombre} - {self.plataforma} - {self.modelo_dispositivo}"


class HistorialNotificacion(models.Model):
    """
    Registro de notificaciones enviadas
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('leido', 'Leído'),
        ('error', 'Error'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='codusuario')
    tipo_notificacion = models.ForeignKey(TipoNotificacion, on_delete=models.CASCADE, db_column='idtiponotificacion')
    canal_notificacion = models.ForeignKey(CanalNotificacion, on_delete=models.CASCADE, db_column='idcanalnotificacion')
    dispositivo_movil = models.ForeignKey(DispositivoMovil, on_delete=models.SET_NULL, null=True, blank=True,
                                          db_column='iddispositivomovil')

    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    datos_adicionales = models.JSONField(blank=True, null=True)  # Para metadatos adicionales

    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    error_mensaje = models.TextField(blank=True, null=True)
    intentos = models.IntegerField(default=0)

    class Meta:
        db_table = 'historialnotificacion'
        verbose_name = 'Historial de Notificación'
        verbose_name_plural = 'Historial de Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.usuario.nombre} - {self.titulo} - {self.estado}"


class PlantillaNotificacion(models.Model):
    """
    Plantillas para diferentes tipos de notificaciones
    """
    tipo_notificacion = models.ForeignKey(TipoNotificacion, on_delete=models.CASCADE, db_column='idtiponotificacion')
    canal_notificacion = models.ForeignKey(CanalNotificacion, on_delete=models.CASCADE, db_column='idcanalnotificacion')

    nombre = models.CharField(max_length=100)
    asunto_template = models.CharField(max_length=200, blank=True, null=True)  # Para emails
    titulo_template = models.CharField(max_length=200)
    mensaje_template = models.TextField()

    # Variables disponibles para reemplazar en las plantillas
    variables_disponibles = models.JSONField(default=list,
                                             help_text="Lista de variables disponibles como {nombre}, {fecha}, etc.")

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'plantillanotificacion'
        unique_together = ['tipo_notificacion', 'canal_notificacion']
        verbose_name = 'Plantilla de Notificación'
        verbose_name_plural = 'Plantillas de Notificación'

    def __str__(self):
        return f"{self.nombre} - {self.tipo_notificacion.nombre} - {self.canal_notificacion.nombre}"