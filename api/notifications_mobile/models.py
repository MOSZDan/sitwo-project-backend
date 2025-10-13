from django.db import models
from django.contrib.postgres.fields import JSONField  # Django <3.1; si usas 3.2+ usa models.JSONField
from django.conf import settings

try:
    JSONField  # noqa
except NameError:
    # Django 3.2+ ya trae JSONField en models
    from django.db.models import JSONField  # type: ignore


class ApiEmpresaMN(models.Model):
    id = models.BigIntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "api_empresa"


class UsuarioMN(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    correoelectronico = models.CharField(max_length=255)
    sexo = models.CharField(max_length=50, null=True)
    telefono = models.CharField(max_length=20, null=True)
    idtipousuario = models.IntegerField()
    notificaciones_email = models.BooleanField()
    notificaciones_push = models.BooleanField()
    recibir_notificaciones = models.BooleanField()
    empresa_id = models.BigIntegerField(null=True)

    class Meta:
        managed = False
        db_table = "usuario"

    @property
    def notif_movil_activa(self) -> bool:
        # Freno principal
        return bool(self.recibir_notificaciones and self.notificaciones_push)


class DispositivoMovilMN(models.Model):
    id = models.BigAutoField(primary_key=True)
    token_fcm = models.TextField()
    plataforma = models.CharField(max_length=20)
    modelo_dispositivo = models.CharField(max_length=100, null=True)
    version_app = models.CharField(max_length=20, null=True)
    activo = models.BooleanField()
    fecha_registro = models.DateTimeField()
    ultima_actividad = models.DateTimeField()
    codusuario = models.IntegerField()

    class Meta:
        managed = False
        db_table = "dispositivomovil"


class CanalNotificacionMN(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(null=True)
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = "canalnotificacion"


class TipoNotificacionMN(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True)
    activo = models.BooleanField()

    class Meta:
        managed = False
        db_table = "tiponotificacion"


class HistorialNotificacionMN(models.Model):
    id = models.BigAutoField(primary_key=True)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    datos_adicionales = models.JSONField(null=True) if hasattr(models, "JSONField") else JSONField(null=True)
    estado = models.CharField(max_length=20)
    fecha_creacion = models.DateTimeField()
    fecha_envio = models.DateTimeField(null=True)
    fecha_entrega = models.DateTimeField(null=True)
    fecha_lectura = models.DateTimeField(null=True)
    error_mensaje = models.TextField(null=True)
    intentos = models.IntegerField()
    codusuario = models.IntegerField()
    idtiponotificacion = models.BigIntegerField()
    idcanalnotificacion = models.BigIntegerField()
    iddispositivomovil = models.BigIntegerField(null=True)

    class Meta:
        managed = False
        db_table = "historialnotificacion"


# --- Agenda: Consulta y Horario (unmanaged) ---
class HorarioMN(models.Model):
    id = models.IntegerField(primary_key=True)
    hora = models.TimeField()
    empresa_id = models.BigIntegerField(null=True)

    class Meta:
        managed = False
        db_table = "horario"


class ConsultaMN(models.Model):
    id = models.IntegerField(primary_key=True)
    fecha = models.DateField()
    codpaciente = models.IntegerField()
    cododontologo = models.IntegerField(null=True)
    codrecepcionista = models.IntegerField(null=True)
    idhorario = models.IntegerField()
    idtipoconsulta = models.IntegerField()
    idestadoconsulta = models.IntegerField()
    empresa_id = models.BigIntegerField(null=True)

    class Meta:
        managed = False
        db_table = "consulta"
