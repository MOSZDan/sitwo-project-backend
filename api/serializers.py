from rest_framework import serializers
from .models import (
    Usuario, Paciente, Odontologo, Recepcionista,
    Horario, Tipodeconsulta, Estadodeconsulta, Consulta
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
        fields = ("id","hora",)


class TipodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tipodeconsulta
        fields = ("id", "nombreconsulta")


class EstadodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estadodeconsulta
        fields = ("id", "estado")


# --------- NUEVO SERIALIZER PARA CREAR CONSULTAS ---------
class CreateConsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consulta
        # Campos que el frontend enviará para crear una cita
        fields = (
            'fecha',
            'codpaciente',
            'cododontologo',
            'idhorario',
            'idtipoconsulta',
            'idestadoconsulta',
            # El codrecepcionista es opcional
            'codrecepcionista',
        )


# --------- Consulta (se mantiene igual) ---------
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
        fields = ['idestadoconsulta']

class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar únicamente las preferencias de notificación.
    """
    class Meta:
        model = Usuario
        fields = ['recibir_notificaciones']