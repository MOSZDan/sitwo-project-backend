# api/serializers_auth.py
from rest_framework import serializers
from .models import Paciente  # para chequear unicidad de carnet

ROLES = ("paciente", "odontologo", "recepcionista")

class RegisterSerializer(serializers.Serializer):
    # Credenciales / base
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)

    # Campos base de Usuario
    nombre = serializers.CharField(max_length=255, required=False, allow_blank=True)
    apellido = serializers.CharField(max_length=255, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    sexo = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Catálogo (1=admin, 2=normal). Si no mandas, en views se usa 2 por defecto.
    idtipousuario = serializers.IntegerField(required=False)

    # Subtipo a crear (herencia 1-1). Por defecto "paciente".
    rol = serializers.ChoiceField(choices=ROLES, required=False)

    # ---- Campos de PACIENTE (subtipo) ----
    carnetidentidad = serializers.CharField(max_length=50, required=False, allow_blank=True)
    fechanacimiento = serializers.DateField(required=False, allow_null=True)
    direccion = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        rol = (attrs.get("rol") or "paciente").strip().lower()
        if rol == "paciente":
            # exigir campos de paciente
            faltan = []
            if not attrs.get("sexo"): faltan.append("sexo")
            if not attrs.get("direccion"): faltan.append("direccion")
            if not attrs.get("fechanacimiento"): faltan.append("fechanacimiento")
            if not attrs.get("carnetidentidad"): faltan.append("carnetidentidad")
            if faltan:
                raise serializers.ValidationError(
                    {"detail": f"Faltan campos de paciente: {', '.join(faltan)}"}
                )

            # unicidad de CI si lo mandan
            ci = (attrs.get("carnetidentidad") or "").strip()
            if ci and Paciente.objects.filter(carnetidentidad=ci).exists():
                raise serializers.ValidationError({"carnetidentidad": "El carnet ya existe."})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)
