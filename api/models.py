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
    recibir_notificaciones = models.BooleanField(default=True)
    notificaciones_email = models.BooleanField(default=True)
    notificaciones_push = models.BooleanField(default=False)
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
    # Antes era OneToOne; ahora es FK para permitir múltiples episodios por paciente
    pacientecodigo = models.ForeignKey(
        'Paciente',
        on_delete=models.DO_NOTHING,
        db_column='pacientecodigo',
        related_name='historias'
    )

    # Campos clínicos existentes
    alergias = models.TextField(blank=True, null=True)
    enfermedades = models.TextField(blank=True, null=True)
    motivoconsulta = models.TextField(blank=True, null=True)
    diagnostico = models.TextField(blank=True, null=True)

    # NUEVOS (ya creados en la BD con tu script)
    episodio = models.PositiveIntegerField(default=1)     # 1..n por paciente
    fecha = models.DateTimeField(auto_now_add=True)       # timestamptz DEFAULT now()
    updated_at = models.DateTimeField(auto_now=True)      # timestamptz DEFAULT now()

    class Meta:
        db_table = 'historialclinico'
        constraints = [
            models.UniqueConstraint(
                fields=['pacientecodigo', 'episodio'],
                name='uniq_historial_paciente_episodio'
            )
        ]
        ordering = ['-fecha', '-episodio']

    def __str__(self):
        return f'HCE paciente={self.pacientecodigo_id} episodio={self.episodio}'

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
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


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


class Vista(models.Model):
    """
    Modelo para gestión de vistas/pantallas y permisos por roles
    """
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    ruta = models.CharField(max_length=200)
    plataforma = models.CharField(max_length=50)  # web, mobile, etc.
    descripcion = models.TextField(blank=True, null=True)
    roles_permitidos = models.ManyToManyField(Tipodeusuario, blank=True)

    class Meta:
        db_table = 'vista'
        verbose_name = 'Vista'
        verbose_name_plural = 'Vistas'

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


# ============================================================================
# TABLA DE AUDITORÍA
# ============================================================================
class Bitacora(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='codusuario')
    accion = models.CharField(max_length=100)
    tabla_afectada = models.CharField(max_length=100)
    registro_id = models.IntegerField()
    valores_anteriores = models.JSONField(null=True, blank=True)
    valores_nuevos = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bitacora'
        verbose_name = 'Bitácora'
        verbose_name_plural = 'Bitácoras'

    def __str__(self):
        return f"{self.usuario.nombre} - {self.accion} - {self.tabla_afectada} - {self.timestamp}"
