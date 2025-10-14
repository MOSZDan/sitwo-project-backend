from rest_framework import serializers
from django.db.models import Q
import re
from .models import (
    Usuario, Paciente, Odontologo, Recepcionista,
    Horario, Tipodeconsulta, Estadodeconsulta, Consulta,
    Tipodeusuario,   # ← roles
    Historialclinico,  # ← NUEVO: HCE
    Consentimiento, # <-- NUEVO: Consentimiento
)
from .models import Estadodeconsulta
from rest_framework.validators import UniqueTogetherValidator

# --------- Usuarios / Pacientes ---------

class UsuarioMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("codigo", "nombre", "apellido", "correoelectronico", "telefono")


class PacienteSerializer(serializers.ModelSerializer):
    # OneToOne a Usuario (solo lectura, anidado)
    codusuario = UsuarioMiniSerializer(read_only=True)

    class Meta:
        model = Paciente
        fields = "__all__"


# Versión mini de Paciente para anidar en otras respuestas
class PacienteMiniSerializer(serializers.ModelSerializer):
    codusuario = UsuarioMiniSerializer(read_only=True)

    class Meta:
        model = Paciente
        fields = ("codusuario", "carnetidentidad")


# --------- Minis para relaciones de Consulta ---------

class OdontologoMiniSerializer(serializers.ModelSerializer):
    codusuario = UsuarioMiniSerializer(read_only=True)
    codigo = serializers.IntegerField(source='codusuario.codigo', read_only=True)

    class Meta:
        model = Odontologo
        fields = ("codigo", "codusuario", "especialidad", "nromatricula")


class RecepcionistaMiniSerializer(serializers.ModelSerializer):
    codusuario = UsuarioMiniSerializer(read_only=True)

    class Meta:
        model = Recepcionista
        fields = ("codusuario",)


class HorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Horario
        fields = ("id", "hora",)


class TipodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tipodeconsulta
        fields = ("id", "nombreconsulta")


class EstadodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estadodeconsulta
        fields = ("id", "estado")


# --------- Crear / Detalle / Actualizar Consulta ---------

class CreateConsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consulta
        fields = (
            "fecha",
            "codpaciente",
            "cododontologo",
            "idhorario",
            "idtipoconsulta",
            "idestadoconsulta",
            "codrecepcionista",
        )


    def validate(self, data):
        """
        Validar que no exista ya una consulta para el mismo odontólogo,
        en la misma fecha y horario.
        """
        if Consulta.objects.filter(
            cododontologo=data['cododontologo'],
            fecha=data['fecha'],
            idhorario=data['idhorario']
            # Opcional: Excluir citas canceladas si se permite re-agendar sobre ellas
            # ).exclude(idestadoconsulta__in=[3, 4]
        ).exists():
            raise serializers.ValidationError(
                "Este horario ya está reservado con el odontólogo seleccionado."
            )
        return data


# --- NUEVO: Serializador para Reprogramar Cita ---
class EstadodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estadodeconsulta
        fields = "__all__"

class ReprogramarConsultaSerializer(serializers.Serializer):
    """
    Serializador para validar los datos al reprogramar una cita.
    """
    fecha = serializers.DateField()
    idhorario = serializers.PrimaryKeyRelatedField(queryset=Horario.objects.all())

    def validate(self, data):
        """
        Valida que el nuevo horario para reprogramar esté disponible.
        El 'cododontologo' se inyecta desde la vista.
        """
        from datetime import date

        consulta = self.context.get('consulta')
        if not consulta:
            # Este error no debería ocurrir si se usa correctamente desde la vista
            raise serializers.ValidationError("No se encontró la consulta a reprogramar.")

        # VALIDACIÓN 1: No permitir reprogramar citas vencidas
        if consulta.fecha < date.today():
            raise serializers.ValidationError(
                "No se puede reprogramar una cita que ya pasó de fecha. La cita debe ser cancelada."
            )

        # VALIDACIÓN 2: La nueva fecha debe ser futura
        if data['fecha'] < date.today():
            raise serializers.ValidationError(
                "No se puede reprogramar una cita a una fecha pasada."
            )

        cododontologo = consulta.cododontologo

        # VALIDACIÓN 3: Validar que el nuevo horario no esté ya ocupado por otra cita
        if Consulta.objects.filter(
            cododontologo=cododontologo,
            fecha=data['fecha'],
            idhorario=data['idhorario']
        ).exclude(pk=consulta.pk).exists(): # Excluimos la cita actual
            raise serializers.ValidationError(
                "El nuevo horario seleccionado no está disponible."
            )
        return data

# --------- Consulta ---------

class ConsultaSerializer(serializers.ModelSerializer):
    codpaciente = PacienteMiniSerializer(read_only=True)
    cododontologo = OdontologoMiniSerializer(read_only=True)
    codrecepcionista = RecepcionistaMiniSerializer(read_only=True)
    idhorario = HorarioSerializer(read_only=True)
    idtipoconsulta = TipodeconsultaSerializer(read_only=True)
    idestadoconsulta = EstadodeconsultaSerializer(read_only=True)

    class Meta:
        model = Consulta
        fields = "__all__"


class UpdateConsultaSerializer(serializers.ModelSerializer):
    """
    Serializador específico para actualizar solo el estado de una consulta.
    """
    class Meta:
        model = Consulta
        fields = ["idestadoconsulta"]


# --------- ADMIN: Roles y Usuarios (lista + cambio de rol) ---------

class TipodeusuarioSerializer(serializers.ModelSerializer):
    # 'identificacion' visible en la API, tomado del PK real 'id'
    identificacion = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Tipodeusuario
        fields = ("identificacion", "rol", "descripcion")


class UsuarioAdminSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source="idtipousuario.rol", read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')

        qs = Tipodeusuario.objects.all()
        # Mostrar SOLO roles del tenant + globales (empresa IS NULL)
        if request and hasattr(request, 'tenant') and request.tenant:
            emp = request.tenant
            qs = qs.filter(Q(empresa=emp) | Q(empresa__isnull=True))

        self.fields['idtipousuario'] = serializers.PrimaryKeyRelatedField(
            queryset=qs, required=False
        )

    class Meta:
        model = Usuario
        fields = ("codigo", "nombre", "apellido", "correoelectronico", "idtipousuario", "rol")
    # 'codigo' viene de BD/negocio, lo dejamos de solo lectura si así lo manejan
        read_only_fields = ("codigo",)

    def update(self, instance, validated_data):
        new_role = validated_data.get("idtipousuario")
        if new_role and new_role.empresa_id not in (None, instance.empresa_id):
            raise serializers.ValidationError("El rol pertenece a otra empresa.")

            # 2) Regla opcional: no remover al último Administrador de la empresa
        was_admin = bool(instance.idtipousuario and instance.idtipousuario.rol.strip().lower() == 'administrador')
        will_be_admin = bool(new_role and new_role.rol.strip().lower() == 'administrador')
        if was_admin and not will_be_admin:
            remaining  = (
                Usuario.objects
                .filter(empresa=instance.empresa, idtipousuario__rol__iexact='Administrador')
                .exclude(pk=instance.pk)
                .count()
            )
            if remaining == 0:
                raise serializers.ValidationError("No puedes remover el último administrador de la empresa.")
        return super().update(instance, validated_data)


class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar únicamente las preferencias de notificación.
    """
    class Meta:
        model = Usuario
        fields = ['recibir_notificaciones']


# --------- PERFIL (GET/PATCH de la propia fila en `usuario`) ---------
class PacienteProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ('direccion', 'fechanacimiento', 'carnetidentidad')


class OdontologoProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Odontologo
        fields = ('especialidad', 'experienciaProfesional', 'noMatricula')


class RecepcionistaProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recepcionista
        fields = ('habilidadesSoftware',)



class UsuarioMeSerializer(serializers.ModelSerializer):
    """
    Gestiona la lectura y actualización del perfil del usuario autenticado.
    SOLO permite editar: correoelectronico, telefono y password
    """
    perfil = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Usuario
        fields = (
            'codigo', 'nombre', 'apellido', 'telefono',
            'correoelectronico', 'sexo', 'idtipousuario', 'recibir_notificaciones',
            'perfil', 'password', 'password_confirm'
        )
        read_only_fields = ('codigo', 'nombre', 'apellido', 'sexo', 'idtipousuario', 'recibir_notificaciones', 'perfil')

    def get_perfil(self, instance):
        role_id = instance.idtipousuario_id
        if role_id == 2 and hasattr(instance, 'paciente'):
            return PacienteProfileSerializer(instance.paciente).data
        elif role_id == 4 and hasattr(instance, 'odontologo'):
            return OdontologoProfileSerializer(instance.odontologo).data
        elif role_id == 3 and hasattr(instance, 'recepcionista'):
            return RecepcionistaProfileSerializer(instance.recepcionista).data
        return None

    def validate_correoelectronico(self, value):
        value = value.lower().strip()
        usuario_actual = self.instance
        if Usuario.objects.filter(correoelectronico=value).exclude(codigo=usuario_actual.codigo).exists():
            raise serializers.ValidationError("Este correo electrónico ya está en uso por otro usuario.")
        return value

    def validate_telefono(self, value):
        """Valida formato de teléfono (8-15 dígitos, puede incluir +, espacios y guiones)"""
        value = (value or "").strip()
        if not value:
            return value
        
        # Remover caracteres permitidos para validar solo números
        numeros = re.sub(r'[\s\-\+\(\)]', '', value)
        
        # Validar que tenga entre 8 y 15 dígitos
        if not re.match(r'^\d{8,15}$', numeros):
            raise serializers.ValidationError(
                "El teléfono debe contener entre 8 y 15 dígitos. "
                "Puede incluir +, espacios, guiones y paréntesis."
            )
        return value

    def validate(self, attrs):
        password = attrs.get('password', '')
        password_confirm = attrs.get('password_confirm', '')
        if password or password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
            if password and len(password) < 6:
                raise serializers.ValidationError({'password': 'La contraseña debe tener al menos 6 caracteres.'})
        return attrs

    def update(self, instance, validated_data):
        """
        Lógica de actualización corregida y más segura.
        """
        from django.contrib.auth.models import User

        # Obtener el usuario de Django asociado (asumiendo que el username es el email)
        try:
            django_user = User.objects.get(username=instance.correoelectronico)
        except User.DoesNotExist:
            django_user = None

        # Actualizar contraseña si se proporcionó
        password = validated_data.get('password')
        if password and django_user:
            django_user.set_password(password)

        # Actualizar correo electrónico si cambió
        nuevo_email = validated_data.get('correoelectronico')
        if nuevo_email and nuevo_email != instance.correoelectronico:
            instance.correoelectronico = nuevo_email
            if django_user:
                django_user.username = nuevo_email
                django_user.email = nuevo_email

        # Actualizar teléfono
        instance.telefono = validated_data.get('telefono', instance.telefono)

        # Guardar los cambios
        instance.save()
        if django_user:
            django_user.save()

        return instance

#para notificaciones
class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer para gestionar las preferencias de notificaciones del usuario.
    """

    class Meta:
        model = Usuario
        fields = ['notificaciones_email', 'notificaciones_push']

    def update(self, instance, validated_data):
        instance.notificaciones_email = validated_data.get('notificaciones_email', instance.notificaciones_email)
        instance.notificaciones_push = validated_data.get('notificaciones_push', instance.notificaciones_push)
        instance.save()
        return instance


# =========================
#   NUEVO: Historias Clínicas (HCE)
# =========================
from django.utils import timezone
from django.db.models import Max

class HistorialclinicoCreateSerializer(serializers.ModelSerializer):
    """
    Crea una HCE (episodio) para un paciente.
    Regla anti-duplicado: mismo día + mismo motivo -> requiere forzar_nuevo_episodio=true
    """
    pacientecodigo = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.all())
    forzar_nuevo_episodio = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Historialclinico
        fields = [
            'id',  # ← AGREGADO para que se devuelva en la respuesta
            'pacientecodigo',
            'alergias', 'enfermedades', 'motivoconsulta', 'diagnostico',
            'forzar_nuevo_episodio',
        ]
        read_only_fields = ['id']  # ← AGREGADO: id es solo lectura (auto-generado)

    def validate(self, attrs):
        if not (attrs.get('motivoconsulta') or '').strip():
            raise serializers.ValidationError('El motivo de consulta es obligatorio.')
        return attrs

    def create(self, validated):
        paciente = validated['pacientecodigo']
        forzar = validated.pop('forzar_nuevo_episodio', False)

        # siguiente episodio para este paciente
        max_epi = Historialclinico.objects.filter(pacientecodigo=paciente)\
                                          .aggregate(Max('episodio'))['episodio__max'] or 0

        # posible duplicado en el día por mismo motivo
        hoy = timezone.localdate()
        dup = Historialclinico.objects.filter(
            pacientecodigo=paciente,
            motivoconsulta=(validated.get('motivoconsulta') or '').strip(),
            fecha__date=hoy
        ).first()

        if dup and not forzar:
            raise serializers.ValidationError({
                'duplicado': 'Ya existe una HCE hoy con el mismo motivo. Envíe forzar_nuevo_episodio=true para abrir un nuevo episodio.'
            })

        hce = Historialclinico.objects.create(
            episodio=max_epi + 1,
            **validated
        )
        return hce


class HistorialclinicoListSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='pacientecodigo.codusuario.nombre', read_only=True)
    paciente_apellido = serializers.CharField(source='pacientecodigo.codusuario.apellido', read_only=True)

    class Meta:
        model = Historialclinico
        fields = [
            'id', 'pacientecodigo', 'paciente_nombre', 'paciente_apellido',
            'episodio', 'fecha',
            'alergias', 'enfermedades', 'motivoconsulta', 'diagnostico',
            'updated_at',
        ]

# =========================
#   NUEVO: Consentimiento Digital
# =========================
class ConsentimientoSerializer(serializers.ModelSerializer):
    """
    Serializador para crear y listar consentimientos digitales.
    El campo `paciente` se espera como un ID al crear.
    """
    # Campos de solo lectura para mostrar info útil en la API
    paciente_nombre = serializers.CharField(source='paciente.codusuario.nombre', read_only=True)
    paciente_apellido = serializers.CharField(source='paciente.codusuario.apellido', read_only=True)
    fecha_creacion_formateada = serializers.DateTimeField(source='fecha_creacion', format="%d/%m/%Y %H:%M", read_only=True)
    
    # Campos de sellado digital (solo lectura)
    fecha_hora_sello = serializers.DateTimeField(read_only=True)
    hash_documento = serializers.CharField(read_only=True)
    fecha_validacion = serializers.DateTimeField(read_only=True)
    
    # Campo para mostrar quién validó el consentimiento
    validado_por_nombre = serializers.CharField(source='validado_por.nombre', read_only=True)
    validado_por_apellido = serializers.CharField(source='validado_por.apellido', read_only=True)

    class Meta:
        model = Consentimiento
        fields = (
            'id',
            'paciente', 
            'consulta', 
            'plan_tratamiento',
            'titulo', 
            'texto_contenido',
            'firma_base64',
            # Campos de solo lectura
            'paciente_nombre',
            'paciente_apellido',
            'fecha_creacion',
            'fecha_creacion_formateada',
            'ip_creacion',
            'empresa',
            # Campos de sellado digital
            'fecha_hora_sello',
            'hash_documento',
            'fecha_validacion',
            'validado_por_nombre',
            'validado_por_apellido',
        )
        # Campos que no se deben requerir en la entrada (POST/PUT)
        read_only_fields = (
            'fecha_creacion',
            'ip_creacion',
            'empresa',
            'fecha_hora_sello',
            'hash_documento',
            'fecha_validacion',
            'validado_por',
            'id',
            'paciente_nombre',
            'paciente_apellido',
            'fecha_creacion_formateada',
        )

    def create(self, validated_data):
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError({
                "error": "No se pudo obtener el contexto de la petición",
                "detail": "El serializador requiere acceso al objeto request"
            })
        
        # Validar y asignar el tenant (empresa)
        if not hasattr(request, 'tenant') or not request.tenant:
            raise serializers.ValidationError({
                "error": "No se pudo determinar el tenant",
                "detail": "Se requiere un tenant válido para crear consentimientos",
                "debug_info": {
                    "user": str(request.user),
                    "path": request.path,
                    "method": request.method
                }
            })
        
        # Asignar la empresa explícitamente
        empresa = request.tenant
        if not empresa.id:
            raise serializers.ValidationError({
                "error": "Tenant inválido",
                "detail": "El tenant no tiene un ID válido"
            })
            
        validated_data['empresa_id'] = empresa.id
        
        # Extraer la IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        validated_data['ip_creacion'] = ip

        try:
            instance = super().create(validated_data)
            print(f"Consentimiento creado exitosamente: ID={instance.id}, empresa_id={instance.empresa_id}")
            return instance
        except Exception as e:
            print(f"Error al crear el consentimiento: {str(e)}")
            print(f"Datos validados: {validated_data}")
            raise

# =====================================
# REGISTRO PÚBLICO DE EMPRESAS (SaaS)
# =====================================

from .models import Empresa
import re

class RegistroEmpresaSerializer(serializers.Serializer):
    """
    Serializador para el registro público de nuevas empresas (clientes SaaS).
    Este endpoint NO requiere autenticación.
    """
    # Datos de la empresa
    nombre_empresa = serializers.CharField(max_length=255)
    subdomain = serializers.CharField(
        max_length=100,
        help_text="Subdominio único (ej: clinica-norte, dentcare)"
    )

    # Datos del usuario administrador
    nombre_admin = serializers.CharField(max_length=255)
    apellido_admin = serializers.CharField(max_length=255)
    email_admin = serializers.EmailField()
    telefono_admin = serializers.CharField(max_length=20, required=False, allow_blank=True)
    sexo_admin = serializers.ChoiceField(
        choices=['Masculino', 'Femenino', 'Otro'],
        required=False,
        allow_blank=True
    )

    def validate_subdomain(self, value):
        """Valida que el subdominio sea único y tenga formato válido"""
        # Convertir a minúsculas y limpiar
        value = value.lower().strip()

        # Validar formato: solo letras, números y guiones
        if not re.match(r'^[a-z0-9-]+$', value):
            raise serializers.ValidationError(
                "El subdominio solo puede contener letras minúsculas, números y guiones."
            )

        # Validar longitud
        if len(value) < 3:
            raise serializers.ValidationError("El subdominio debe tener al menos 3 caracteres.")

        if len(value) > 50:
            raise serializers.ValidationError("El subdominio no puede tener más de 50 caracteres.")

        # Validar que no empiece o termine con guión
        if value.startswith('-') or value.endswith('-'):
            raise serializers.ValidationError("El subdominio no puede empezar o terminar con guión.")

        # Subdominios reservados
        subdominios_reservados = [
            'www', 'api', 'admin', 'app', 'blog', 'mail', 'ftp',
            'localhost', 'server', 'ns1', 'ns2', 'smtp', 'pop',
            'imap', 'webmail', 'email', 'portal', 'dashboard',
            'sistema', 'test', 'dev', 'staging', 'prod', 'production'
        ]

        if value in subdominios_reservados:
            raise serializers.ValidationError(
                f"El subdominio '{value}' está reservado. Por favor elige otro."
            )

        # Validar que no exista en la BD
        if Empresa.objects.filter(subdomain__iexact=value).exists():
            raise serializers.ValidationError(
                f"El subdominio '{value}' ya está en uso. Por favor elige otro."
            )

        return value

    def validate_email_admin(self, value):
        """Valida que el email del admin no esté registrado"""
        value = value.lower().strip()

        if Usuario.objects.filter(correoelectronico__iexact=value).exists():
            raise serializers.ValidationError(
                "Este correo electrónico ya está registrado en el sistema."
            )

        return value

    def validate_nombre_empresa(self, value):
        """Valida que el nombre de la empresa sea único"""
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError("El nombre de la empresa debe tener al menos 3 caracteres.")

        if Empresa.objects.filter(nombre__iexact=value).exists():
            raise serializers.ValidationError(
                f"Ya existe una empresa con el nombre '{value}'. Por favor usa otro nombre."
            )

        return value


class ValidarSubdominioSerializer(serializers.Serializer):
    """
    Serializador para validar si un subdominio está disponible.
    Usado por el frontend para validación en tiempo real.
    """
    subdomain = serializers.CharField(max_length=100)

    def validate_subdomain(self, value):
        """Valida formato y disponibilidad del subdominio"""
        value = value.lower().strip()

        # Validar formato
        if not re.match(r'^[a-z0-9-]+$', value):
            raise serializers.ValidationError(
                "El subdominio solo puede contener letras minúsculas, números y guiones."
            )

        if len(value) < 3:
            raise serializers.ValidationError("El subdominio debe tener al menos 3 caracteres.")

        # Subdominios reservados
        subdominios_reservados = [
            'www', 'api', 'admin', 'app', 'blog', 'mail', 'ftp',
            'localhost', 'server', 'ns1', 'ns2', 'smtp', 'pop'
        ]

        if value in subdominios_reservados:
            raise serializers.ValidationError("Este subdominio está reservado.")

        # Verificar disponibilidad
        if Empresa.objects.filter(subdomain__iexact=value).exists():
            raise serializers.ValidationError("Este subdominio ya está en uso.")

        return value


class EmpresaPublicSerializer(serializers.ModelSerializer):
    """
    Serializador público para mostrar información básica de empresas.
    Solo incluye datos que pueden ser públicos.
    """
    class Meta:
        model = Empresa
        fields = ['id', 'nombre', 'subdomain', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion', 'activo']


# api/serializers.py - Agregar al final del archivo existente

from .models import Bitacora


class BitacoraSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)
    fecha_hora_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Bitacora
        fields = [
            'id', 'accion', 'accion_display', 'descripcion',
            'fecha_hora', 'fecha_hora_formatted', 'usuario', 'usuario_nombre',
            'ip_address', 'user_agent', 'modelo_afectado', 'objeto_id',
            'datos_adicionales'
        ]
        read_only_fields = ['id', 'fecha_hora']

    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return f"{obj.usuario.nombre} {obj.usuario.apellido}"
        return "Usuario anónimo"

    def get_fecha_hora_formatted(self, obj):
        return obj.fecha_hora.strftime('%d/%m/%Y %H:%M:%S')


# Función auxiliar para crear registros de bitácora manualmente
def crear_registro_bitacora(accion, usuario=None, ip_address='127.0.0.1', descripcion='',
                            modelo_afectado=None, objeto_id=None, datos_adicionales=None):
    """
    Función auxiliar para crear registros de bitácora desde las vistas
    """
    return Bitacora.objects.create(
        accion=accion,
        descripcion=descripcion,
        usuario=usuario,
        ip_address=ip_address,
        modelo_afectado=modelo_afectado,
        objeto_id=objeto_id,
        datos_adicionales=datos_adicionales or {}
    )


# ============================================================================
# DOCUMENTOS CLÍNICOS - S3
# ============================================================================
from .models import DocumentoClinico
from django.core.validators import FileExtensionValidator

class DocumentoClinicoSerializer(serializers.ModelSerializer):
    """Serializer para listar y detallar documentos clínicos"""
    profesional_nombre = serializers.SerializerMethodField()
    paciente_nombre = serializers.SerializerMethodField()
    tamanio_mb = serializers.SerializerMethodField()
    url_firmada = serializers.SerializerMethodField()  # ← NUEVO: URL firmada temporal

    class Meta:
        model = DocumentoClinico
        fields = [
            'id', 'codpaciente', 'idconsulta', 'idhistorialclinico',
            'tipo_documento', 'nombre_archivo', 'url_s3', 'tamanio_bytes',
            'tamanio_mb', 'extension', 'profesional_carga', 'profesional_nombre',
            'paciente_nombre', 'fecha_documento', 'notas', 'fecha_creacion',
            'url_firmada'  # ← NUEVO
        ]
        read_only_fields = [
            'id', 'url_s3', 's3_key', 'tamanio_bytes', 'extension',
            'profesional_carga', 'fecha_creacion'
        ]

    def get_profesional_nombre(self, obj):
        if obj.profesional_carga:
            return f"{obj.profesional_carga.nombre} {obj.profesional_carga.apellido}"
        return None

    def get_paciente_nombre(self, obj):
        if obj.codpaciente and obj.codpaciente.codusuario:
            usuario = obj.codpaciente.codusuario
            return f"{usuario.nombre} {usuario.apellido}"
        return None

    def get_tamanio_mb(self, obj):
        """Convierte bytes a MB para mejor lectura"""
        return round(obj.tamanio_bytes / (1024 * 1024), 2)

    def get_url_firmada(self, obj):
        """Genera URL firmada válida por 1 hora para acceso seguro"""
        try:
            import boto3
            from django.conf import settings

            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': obj.s3_key
                },
                ExpiresIn=3600  # 1 hora
            )
            return url
        except Exception as e:
            return None


class DocumentoClinicoUploadSerializer(serializers.Serializer):
    """Serializer para validar la subida de documentos clínicos"""
    archivo = serializers.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'dcm', 'dicom']
            )
        ]
    )
    codpaciente = serializers.IntegerField()
    idconsulta = serializers.IntegerField(required=False, allow_null=True)
    idhistorialclinico = serializers.IntegerField(required=False, allow_null=True)
    tipo_documento = serializers.ChoiceField(choices=DocumentoClinico.TIPO_CHOICES)
    fecha_documento = serializers.DateField()
    notas = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_archivo(self, value):
        """Valida el tamaño máximo del archivo (10MB)"""
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "El archivo no debe exceder 10MB. Tamaño actual: {:.2f}MB".format(
                    value.size / (1024 * 1024)
                )
            )
        return value

    def validate_codpaciente(self, value):
        """Valida que el paciente exista"""
        if not Paciente.objects.filter(codusuario=value).exists():
            raise serializers.ValidationError("El paciente especificado no existe.")
        return value

    def validate(self, attrs):
        """Validaciones adicionales a nivel de objeto"""
        codpaciente = attrs.get('codpaciente')
        idconsulta = attrs.get('idconsulta')
        idhistorialclinico = attrs.get('idhistorialclinico')

        # Si se proporciona consulta, validar que pertenezca al paciente
        if idconsulta:
            if not Consulta.objects.filter(
                id=idconsulta,
                codpaciente__codusuario=codpaciente
            ).exists():
                raise serializers.ValidationError(
                    "La consulta especificada no pertenece al paciente."
                )

        # Si se proporciona historial, validar que pertenezca al paciente
        if idhistorialclinico:
            if not Historialclinico.objects.filter(
                id=idhistorialclinico,
                pacientecodigo__codusuario=codpaciente
            ).exists():
                raise serializers.ValidationError(
                    "El historial clínico especificado no pertenece al paciente."
                )

        return attrs
