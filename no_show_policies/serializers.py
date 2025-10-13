from rest_framework import serializers
from api.models import Estadodeconsulta
from .models import PoliticaNoShow, Multa


class PoliticaNoShowSerializer(serializers.ModelSerializer):
    # Campos de solo lectura “amigables” para UI
    estado_consulta_nombre = serializers.CharField(source='estado_consulta.estado', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = PoliticaNoShow
        fields = '__all__'  # incluye los dos campos extra anteriores
        read_only_fields = ('empresa',)  # la asignamos desde el backend

    def validate(self, attrs):
        bloqueo_temporal = attrs.get(
            'bloqueo_temporal',
            getattr(self.instance, 'bloqueo_temporal', False)
        )
        dias_bloqueo = attrs.get(
            'dias_bloqueo',
            getattr(self.instance, 'dias_bloqueo', None)
        )

        if bloqueo_temporal and (not dias_bloqueo or int(dias_bloqueo) <= 0):
            raise serializers.ValidationError("dias_bloqueo debe ser > 0 cuando bloqueo_temporal es True.")

        if not bloqueo_temporal:
            # Normaliza: si no hay bloqueo, días en null
            attrs['dias_bloqueo'] = None

        return attrs


class EstadodeconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estadodeconsulta
        fields = ['id', 'estado', 'empresa']


class MultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Multa
        fields = '__all__'