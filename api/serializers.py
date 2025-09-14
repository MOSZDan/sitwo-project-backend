from rest_framework import serializers
from .models import (
    Usuario, Paciente, Odontologo, Recepcionista,
    Horario, Tipodeconsulta, Estadodeconsulta, Consulta,
    Tipodeusuario,  # ← roles
    Vista,  # ← NUEVO: para gestión de permisos
)


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

    class Meta:
        model = Odontologo
        fields = ("codusuario", "especialidad", "nromatricula")


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
        # Campos que el frontend enviará para crear una cita
        fields = (
            "fecha",
            "codpaciente",
            "cododontologo",
            "idhorario",
            "idtipoconsulta",
            "idestadoconsulta",
            # opcional
            "codrecepcionista",
        )


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
    idtipousuario = serializers.PrimaryKeyRelatedField(
        queryset=Tipodeusuario.objects.all(), required=False
    )

    class Meta:
        model = Usuario
        fields = (
            "codigo",
            "nombre",
            "apellido",
            "correoelectronico",
            "idtipousuario",
            "rol",
        )
        # 'codigo' viene de BD/negocio, lo dejamos de solo lectura si así lo manejan
        read_only_fields = ("codigo",)

    def update(self, instance, validated_data):
        new_role = validated_data.get("idtipousuario")
        if new_role and instance.idtipousuario_id == 1 and new_role.id != 1:
            remaining_admins = (
                Usuario.objects
                .filter(idtipousuario_id=1)
                .exclude(pk=instance.pk)
                .count()
            )
            if remaining_admins == 0:
                raise serializers.ValidationError(
                    "No puedes remover el último administrador del sistema."
                )
        return super().update(instance, validated_data)


class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar únicamente las preferencias de notificación.
    """

    class Meta:
        model = Usuario
        fields = ['recibir_notificaciones']


# --------- NUEVO: Vista (gestión de permisos por roles) ---------

class VistaSerializer(serializers.ModelSerializer):
    # trabajamos por ids de Tipodeusuario
    roles_permitidos = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tipodeusuario.objects.all(), required=False
    )

    class Meta:
        model = Vista
        fields = (
            "id",
            "codigo",
            "nombre",
            "ruta",
            "plataforma",
            "descripcion",
            "roles_permitidos",
        )


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


# --- Serializer Principal para el Perfil del Usuario ---
class UsuarioMeSerializer(serializers.ModelSerializer):
    """
    Gestiona la lectura y actualización del perfil del usuario autenticado,
    incluyendo los campos específicos de su rol.
    """
    # Campo dinámico que mostrará el perfil correcto (paciente, odontologo, etc.)
    perfil = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        # Campos comunes que siempre se mostrarán
        fields = (
            'codigo', 'nombre', 'apellido', 'telefono',
            'correoelectronico', 'sexo', 'perfil'
        )
        read_only_fields = ('codigo', 'correoelectronico', 'perfil')

    def get_perfil(self, instance):
        """
        Esta función se ejecuta al LEER (GET) los datos.
        Devuelve un diccionario con los datos del perfil específico del usuario.
        """
        # El 'idtipousuario_id' viene de tu modelo Usuario y nos dice el rol.
        role_id = instance.idtipousuario_id

        if role_id == 2 and hasattr(instance, 'paciente'):  # 2 = Paciente
            return PacienteProfileSerializer(instance.paciente).data
        elif role_id == 4 and hasattr(instance, 'odontologo'):  # 4 = Odontologo
            return OdontologoProfileSerializer(instance.odontologo).data
        elif role_id == 3 and hasattr(instance, 'recepcionista'):  # 3 = Recepcionista
            return RecepcionistaProfileSerializer(instance.recepcionista).data

        return None  # Si no tiene un perfil específico

    def update(self, instance, validated_data):
        """
        Esta función se ejecuta al GUARDAR (PATCH/PUT) los datos.
        """
        # 1. Actualiza los campos comunes del modelo Usuario
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.apellido = validated_data.get('apellido', instance.apellido)
        instance.telefono = validated_data.get('telefono', instance.telefono)
        instance.save()

        # 2. Revisa los datos que llegaron en la petición (`self.context['request'].data`)
        #    y actualiza el perfil correspondiente.
        request_data = self.context['request'].data
        role_id = instance.idtipousuario_id

        if role_id == 2 and hasattr(instance, 'paciente'):
            paciente_serializer = PacienteProfileSerializer(
                instance.paciente, data=request_data, partial=True
            )
            paciente_serializer.is_valid(raise_exception=True)
            paciente_serializer.save()

        elif role_id == 4 and hasattr(instance, 'odontologo'):
            odontologo_serializer = OdontologoProfileSerializer(
                instance.odontologo, data=request_data, partial=True
            )
            odontologo_serializer.is_valid(raise_exception=True)
            odontologo_serializer.save()

        elif role_id == 3 and hasattr(instance, 'recepcionista'):
            recepcionista_serializer = RecepcionistaProfileSerializer(
                instance.recepcionista, data=request_data, partial=True
            )
            recepcionista_serializer.is_valid(raise_exception=True)
            recepcionista_serializer.save()

        return instance