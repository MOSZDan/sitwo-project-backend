# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Usuario(models.Model):
    codigo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    correoelectronico = models.CharField(unique=True, max_length=255)
    sexo = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    idtipousuario = models.ForeignKey('Tipodeusuario', models.DO_NOTHING, db_column='idtipousuario')

    class Meta:
        #managed = False
        db_table = 'usuario'


class Paciente(models.Model):
    codusuario = models.OneToOneField(Usuario, models.DO_NOTHING, db_column='codusuario', primary_key=True)
    carnetidentidad = models.CharField(unique=True, max_length=50, blank=True, null=True)
    fechanacimiento = models.DateField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    class Meta:
       # managed = False
        db_table = 'paciente'


class Odontologo(models.Model):
    codusuario = models.OneToOneField(Usuario, models.DO_NOTHING, db_column='codusuario', primary_key=True)
    especialidad = models.CharField(max_length=255, blank=True, null=True)
    experienciaprofesional = models.TextField(blank=True, null=True)
    nromatricula = models.CharField(unique=True, max_length=100, blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'odontologo'


class Recepcionista(models.Model):
    codusuario = models.OneToOneField(Usuario, models.DO_NOTHING, db_column='codusuario', primary_key=True)
    habilidadessoftware = models.TextField(blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'recepcionista'


class Consulta(models.Model):
    fecha = models.DateField()
    codpaciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='codpaciente')
    cododontologo = models.ForeignKey(Odontologo, models.DO_NOTHING, db_column='cododontologo', blank=True, null=True)
    codrecepcionista = models.ForeignKey(Recepcionista, models.DO_NOTHING, db_column='codrecepcionista', blank=True, null=True)
    idhorario = models.ForeignKey('Horario', models.DO_NOTHING, db_column='idhorario')
    idtipoconsulta = models.ForeignKey('Tipodeconsulta', models.DO_NOTHING, db_column='idtipoconsulta')
    idestadoconsulta = models.ForeignKey('Estadodeconsulta', models.DO_NOTHING, db_column='idestadoconsulta')

    class Meta:
        #managed = False
        db_table = 'consulta'


class Tipodeconsulta(models.Model):
    nombreconsulta = models.CharField(max_length=255)

    class Meta:
        #managed = False
        db_table = 'tipodeconsulta'


class Historialclinico(models.Model):
    pacientecodigo = models.OneToOneField(Paciente, models.DO_NOTHING, db_column='pacientecodigo')
    alergias = models.TextField(blank=True, null=True)
    enfermedades = models.TextField(blank=True, null=True)
    motivoconsulta = models.TextField(blank=True, null=True)
    diagnostico = models.TextField(blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'historialclinico'


class Servicio(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    costobase = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        #managed = False
        db_table = 'servicio'


class Insumo(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    stock = models.IntegerField(blank=True, null=True)
    unidaddemedida = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'insumo'


class Medicamento(models.Model):
    nombre = models.CharField(max_length=255)
    cantidadmiligramos = models.CharField(max_length=100, blank=True, null=True)
    presentacion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'medicamento'


class Recetamedica(models.Model):
    codpaciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='codpaciente')
    cododontologo = models.ForeignKey(Odontologo, models.DO_NOTHING, db_column='cododontologo')
    fechaemision = models.DateField()

    class Meta:
        #managed = False
        db_table = 'recetamedica'


class Imtemreceta(models.Model):
    idreceta = models.ForeignKey(Recetamedica, models.DO_NOTHING, db_column='idreceta')
    idmedicamento = models.ForeignKey(Medicamento, models.DO_NOTHING, db_column='idmedicamento')
    posologia = models.TextField()

    class Meta:
        #managed = False
        db_table = 'imtemreceta'


class Plandetratamiento(models.Model):
    codpaciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='codpaciente')
    cododontologo = models.ForeignKey(Odontologo, models.DO_NOTHING, db_column='cododontologo')
    idestado = models.ForeignKey('Estado', models.DO_NOTHING, db_column='idestado')
    fechaplan = models.DateField()
    descuento = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    montototal = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'plandetratamiento'


class Itemplandetratamiento(models.Model):
    idplantratamiento = models.ForeignKey(Plandetratamiento, models.DO_NOTHING, db_column='idplantratamiento')
    idservicio = models.ForeignKey(Servicio, models.DO_NOTHING, db_column='idservicio')
    idpiezadental = models.ForeignKey('Piezadental', models.DO_NOTHING, db_column='idpiezadental', blank=True, null=True)
    idestado = models.ForeignKey('Estado', models.DO_NOTHING, db_column='idestado')
    costofinal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        #managed = False
        db_table = 'itemplandetratamiento'


class Factura(models.Model):
    idplantratamiento = models.ForeignKey(Plandetratamiento, models.DO_NOTHING, db_column='idplantratamiento')
    idestadofactura = models.ForeignKey('Estadodefactura', models.DO_NOTHING, db_column='idestadofactura')
    fechaemision = models.DateField()
    montototal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        #managed = False
        db_table = 'factura'


class Itemdefactura(models.Model):
    idfactura = models.ForeignKey(Factura, models.DO_NOTHING, db_column='idfactura')
    descripcion = models.TextField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        #managed = False
        db_table = 'itemdefactura'


class Pago(models.Model):
    idfactura = models.ForeignKey(Factura, models.DO_NOTHING, db_column='idfactura')
    idtipopago = models.ForeignKey('Tipopago', models.DO_NOTHING, db_column='idtipopago')
    montopagado = models.DecimalField(max_digits=10, decimal_places=2)
    fechapago = models.DateField()

    class Meta:
        #managed = False
        db_table = 'pago'


class Documentoadjunto(models.Model):
    idhistorialclinico = models.ForeignKey(Historialclinico, models.DO_NOTHING, db_column='idhistorialclinico')
    nombredocumento = models.CharField(max_length=255)
    rutaarchivo = models.CharField(max_length=512)
    fechacreacion = models.DateField(blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'documentoadjunto'


class Piezadental(models.Model):
    nombrepieza = models.CharField(max_length=100)
    grupo = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'piezadental'


class Registroodontograma(models.Model):
    idhistorialclinico = models.ForeignKey(Historialclinico, models.DO_NOTHING, db_column='idhistorialclinico')
    idpiezadental = models.ForeignKey(Piezadental, models.DO_NOTHING, db_column='idpiezadental')
    diagnostico = models.TextField(blank=True, null=True)
    fecharegistro = models.DateField()

    class Meta:
        #managed = False
        db_table = 'registroodontograma'


class Horario(models.Model):
    hora = models.TimeField(unique=True)

    class Meta:
        #managed = False
        db_table = 'horario'


class Estado(models.Model):
    estado = models.CharField(unique=True, max_length=100)

    class Meta:
        #managed = False
        db_table = 'estado'


class Estadodeconsulta(models.Model):
    estado = models.CharField(unique=True, max_length=100)

    class Meta:
        #managed = False
        db_table = 'estadodeconsulta'


class Estadodefactura(models.Model):
    estado = models.CharField(unique=True, max_length=100)

    class Meta:
        #managed = False
        db_table = 'estadodefactura'


class Tipodeusuario(models.Model):
    rol = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'tipodeusuario'


class Tipopago(models.Model):
    nombrepago = models.CharField(unique=True, max_length=100)

    class Meta:
        #managed = False
        db_table = 'tipopago'


# ============================================================================
# MODELOS DE NOTIFICACIONES
# ============================================================================

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
    dispositivo_movil = models.ForeignKey(DispositivoMovil, on_delete=models.SET_NULL, null=True, blank=True, db_column='iddispositivomovil')

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
    variables_disponibles = models.JSONField(default=list, help_text="Lista de variables disponibles como {nombre}, {fecha}, etc.")

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