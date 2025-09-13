from rest_framework import serializers
from .models import (
    Usuario, Paciente, Odontologo, Recepcionista,
    Horario, Tipodeconsulta, Estadodeconsulta, Consulta,
    Tipodeusuario,   # ← roles
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
        fields = ("hora",)


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
    """
    Campos que el frontend enviará para crear una cita
    """
    class Meta:
        model = Consulta
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
