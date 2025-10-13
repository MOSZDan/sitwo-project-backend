# api/notifications_mobile/serializers.py
from rest_framework import serializers

__all__ = ["MobileRegisterDeviceSerializerLite", "MobileRegisterDeviceSerializer"]


class _BaseRegisterDeviceSerializer(serializers.Serializer):
    """
    Campos que espera el endpoint de registro de dispositivo.
    Acepta sinónimos comunes desde Flutter/FCM:
      - token_fcm | fcmToken | token | device_token | fcm | registration_token | pushToken | push_token
      - plataforma | platform | os | so | sistema | device_os
    """
    # Canonical
    token_fcm = serializers.CharField(max_length=4096)
    plataforma = serializers.CharField(required=False, allow_blank=True, max_length=20)
    modelo_dispositivo = serializers.CharField(required=False, allow_blank=True, max_length=100)
    version_app = serializers.CharField(required=False, allow_blank=True, max_length=64)

    # Sinónimos de token (write_only para que no rompan si vienen en el payload)
    fcmToken = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4096)
    token = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4096)
    device_token = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4096)
    fcm = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4096)
    registration_token = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4096)
    pushToken = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4096)
    push_token = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=4096)

    # Sinónimos de plataforma
    platform = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)
    os = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)
    so = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)
    sistema = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)
    device_os = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)

    ALT_TOKEN_KEYS = (
        "token_fcm", "fcmToken", "token", "device_token", "fcm",
        "registration_token", "pushToken", "push_token"
    )
    ALT_PLATFORM_KEYS = ("plataforma", "platform", "os", "so", "sistema", "device_os")

    def to_internal_value(self, data):
        """
        Mapea sinónimos → campos canónicos antes de validar.
        Evita errores de 'Unexpected field' y asegura que siempre tengamos token_fcm.
        """
        # Clonar a dict simple (puede venir como QueryDict/OrderedDict)
        d = dict(data)

        # 1) token_fcm: tomar el primero no vacío de los sinónimos
        if not d.get("token_fcm"):
            for k in self.ALT_TOKEN_KEYS:
                v = d.get(k)
                if v and str(v).strip():
                    d["token_fcm"] = str(v).strip()
                    break

        # 2) plataforma: tomar sinónimos si no viene el canónico
        if not d.get("plataforma"):
            for k in self.ALT_PLATFORM_KEYS:
                v = d.get(k)
                if v and str(v).strip():
                    d["plataforma"] = str(v).strip()
                    break

        return super().to_internal_value(d)

    @staticmethod
    def _normalize_plataforma(value: str) -> str:
        v = (value or "").strip().lower()
        if v in {"ios", "iphone", "ipad", "apple"}:
            return "ios"
        if v in {"android", "andr", "a"}:
            return "android"
        return v

    def validate_token_fcm(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("token_fcm es requerido")
        # Evitar basura accidental (espacios, saltos, etc.)
        return v

    def validate_plataforma(self, value: str) -> str:
        # Normaliza; no forzamos choices para no romper clientes antiguos
        return self._normalize_plataforma(value)


class MobileRegisterDeviceSerializerLite(_BaseRegisterDeviceSerializer):
    """
    Para el endpoint /register-lite/ (no persiste).
    """
    pass


class MobileRegisterDeviceSerializer(_BaseRegisterDeviceSerializer):
    """
    Para el endpoint /register-device/ (persiste).
    """
    pass
