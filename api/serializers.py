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
        fields = ("hora",)

class TipodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tipodeconsulta
        fields = ("id", "nombreconsulta")

class EstadodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estadodeconsulta
        fields = ("id", "estado")


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


# NUEVO SERIALIZER PARA CREAR CITAS
class CreateConsultaSerializer(serializers.ModelSerializer):
    """
    Serializer para crear nuevas consultas.
    Acepta los IDs de las relaciones (paciente, odontologo, etc.).
    """
    codpaciente = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.all())
    cododontologo = serializers.PrimaryKeyRelatedField(queryset=Odontologo.objects.all(), required=False, allow_null=True)
    codrecepcionista = serializers.PrimaryKeyRelatedField(queryset=Recepcionista.objects.all(), required=False, allow_null=True)
    idhorario = serializers.PrimaryKeyRelatedField(queryset=Horario.objects.all())
    idtipoconsulta = serializers.PrimaryKeyRelatedField(queryset=Tipodeconsulta.objects.all())
    idestadoconsulta = serializers.PrimaryKeyRelatedField(queryset=Estadodeconsulta.objects.all())

    class Meta:
        model = Consulta
        fields = (
            'fecha',
            'codpaciente',
            'cododontologo',
            'codrecepcionista',
            'idhorario',
            'idtipoconsulta',
            'idestadoconsulta',
        )
