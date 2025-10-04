# api/serializers_notifications.py
from rest_framework import serializers
from .models_notifications import (
    TipoNotificacion, CanalNotificacion, PreferenciaNotificacion,
    DispositivoMovil, HistorialNotificacion, PlantillaNotificacion
)

class TipoNotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoNotificacion
        fields = ['id', 'nombre', 'descripcion', 'activo']


class CanalNotificacionSerializer(serializers.ModelSerializer):
    nombre_display = serializers.CharField(source='get_nombre_display', read_only=True)

    class Meta:
        model = CanalNotificacion
        fields = ['id', 'nombre', 'nombre_display', 'descripcion', 'activo']


class PreferenciaNotificacionSerializer(serializers.ModelSerializer):
    tipo_notificacion_info = TipoNotificacionSerializer(source='tipo_notificacion', read_only=True)
    canal_notificacion_info = CanalNotificacionSerializer(source='canal_notificacion', read_only=True)

    class Meta:
        model = PreferenciaNotificacion
        fields = [
            'id', 'usuario', 'tipo_notificacion', 'canal_notificacion',
            'activo', 'fecha_creacion', 'fecha_actualizacion',
            'tipo_notificacion_info', 'canal_notificacion_info'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class CreatePreferenciaNotificacionSerializer(serializers.ModelSerializer):
    """Serializer simplificado para crear/actualizar preferencias"""

    class Meta:
        model = PreferenciaNotificacion
        fields = ['tipo_notificacion', 'canal_notificacion', 'activo']


class DispositivoMovilSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispositivoMovil
        fields = [
            'id', 'usuario', 'token_fcm', 'plataforma', 'modelo_dispositivo',
            'version_app', 'activo', 'fecha_registro', 'ultima_actividad'
        ]
        read_only_fields = ['fecha_registro', 'ultima_actividad']


class RegisterDispositivoMovilSerializer(serializers.ModelSerializer):
    """Serializer para registrar un nuevo dispositivo móvil"""

    class Meta:
        model = DispositivoMovil
        fields = ['token_fcm', 'plataforma', 'modelo_dispositivo', 'version_app']

    def validate_token_fcm(self, value):
        """Validar que el token FCM no esté vacío"""
        if not value or not value.strip():
            raise serializers.ValidationError("El token FCM es requerido")
        return value.strip()


class HistorialNotificacionSerializer(serializers.ModelSerializer):
    tipo_notificacion_info = TipoNotificacionSerializer(source='tipo_notificacion', read_only=True)
    canal_notificacion_info = CanalNotificacionSerializer(source='canal_notificacion', read_only=True)
    dispositivo_info = DispositivoMovilSerializer(source='dispositivo_movil', read_only=True)

    class Meta:
        model = HistorialNotificacion
        fields = [
            'id', 'usuario', 'tipo_notificacion', 'canal_notificacion',
            'dispositivo_movil', 'titulo', 'mensaje', 'datos_adicionales',
            'estado', 'fecha_creacion', 'fecha_envio', 'fecha_entrega',
            'fecha_lectura', 'error_mensaje', 'intentos',
            'tipo_notificacion_info', 'canal_notificacion_info', 'dispositivo_info'
        ]


class PlantillaNotificacionSerializer(serializers.ModelSerializer):
    tipo_notificacion_info = TipoNotificacionSerializer(source='tipo_notificacion', read_only=True)
    canal_notificacion_info = CanalNotificacionSerializer(source='canal_notificacion', read_only=True)

    class Meta:
        model = PlantillaNotificacion
        fields = [
            'id', 'tipo_notificacion', 'canal_notificacion', 'nombre',
            'asunto_template', 'titulo_template', 'mensaje_template',
            'variables_disponibles', 'activo', 'fecha_creacion', 'fecha_actualizacion',
            'tipo_notificacion_info', 'canal_notificacion_info'
        ]


class PreferenciasUsuarioSerializer(serializers.Serializer):
    """Serializer para mostrar todas las preferencias de un usuario de forma organizada"""
    usuario_id = serializers.IntegerField(read_only=True)
    email_activo = serializers.BooleanField(read_only=True)
    push_activo = serializers.BooleanField(read_only=True)

    # Preferencias por tipo de notificación
    cita_recordatorio_email = serializers.BooleanField(read_only=True)
    cita_recordatorio_push = serializers.BooleanField(read_only=True)
    cita_confirmacion_email = serializers.BooleanField(read_only=True)
    cita_confirmacion_push = serializers.BooleanField(read_only=True)
    cita_cancelacion_email = serializers.BooleanField(read_only=True)
    cita_cancelacion_push = serializers.BooleanField(read_only=True)

    resultado_disponible_email = serializers.BooleanField(read_only=True)
    resultado_disponible_push = serializers.BooleanField(read_only=True)

    factura_generada_email = serializers.BooleanField(read_only=True)
    factura_generada_push = serializers.BooleanField(read_only=True)
    pago_confirmado_email = serializers.BooleanField(read_only=True)
    pago_confirmado_push = serializers.BooleanField(read_only=True)

    # Dispositivos móviles registrados
    dispositivos_moviles = DispositivoMovilSerializer(many=True, read_only=True)


class ActualizarPreferenciasSerializer(serializers.Serializer):
    """Serializer para actualizar múltiples preferencias de una vez"""

    # Preferencias generales
    email_activo = serializers.BooleanField(required=False)
    push_activo = serializers.BooleanField(required=False)

    # Citas
    cita_recordatorio_email = serializers.BooleanField(required=False)
    cita_recordatorio_push = serializers.BooleanField(required=False)
    cita_confirmacion_email = serializers.BooleanField(required=False)
    cita_confirmacion_push = serializers.BooleanField(required=False)
    cita_cancelacion_email = serializers.BooleanField(required=False)
    cita_cancelacion_push = serializers.BooleanField(required=False)

    # Resultados
    resultado_disponible_email = serializers.BooleanField(required=False)
    resultado_disponible_push = serializers.BooleanField(required=False)

    # Facturación
    factura_generada_email = serializers.BooleanField(required=False)
    factura_generada_push = serializers.BooleanField(required=False)
    pago_confirmado_email = serializers.BooleanField(required=False)
    pago_confirmado_push = serializers.BooleanField(required=False)


class EnviarNotificacionSerializer(serializers.Serializer):
    """Serializer para enviar notificaciones manuales desde el admin"""
    usuarios = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Lista de IDs de usuarios a notificar"
    )
    tipo_notificacion = serializers.CharField(max_length=100)
    canales = serializers.ListField(
        child=serializers.CharField(max_length=20),
        help_text="Lista de canales: ['email', 'push']"
    )
    titulo = serializers.CharField(max_length=200)
    mensaje = serializers.CharField()
    datos_adicionales = serializers.JSONField(required=False)

    def validate_canales(self, value):
        canales_validos = ['email', 'push', 'sms', 'whatsapp']
        for canal in value:
            if canal not in canales_validos:
                raise serializers.ValidationError(f"Canal '{canal}' no es válido. Canales válidos: {canales_validos}")
        return value