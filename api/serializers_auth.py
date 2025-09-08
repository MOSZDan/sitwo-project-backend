# api/serializers_auth.py
from rest_framework import serializers
from .models import Paciente

ROLES = ("paciente", "odontologo", "recepcionista")

# Mapea rol -> idtipousuario del catálogo (ajusta si tus IDs reales son otros)
ROLE_TO_TU = {
    "paciente": 2,
    "odontologo": 3,
    "recepcionista": 4,
}


class RegisterSerializer(serializers.Serializer):
    # Credenciales
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)

    # Campos base de Usuario
    nombre = serializers.CharField(max_length=255, required=False, allow_blank=True)
    apellido = serializers.CharField(max_length=255, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    sexo = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Catálogo/rol
    idtipousuario = serializers.IntegerField(required=False)   # el FE puede mandarlo o no
    rol = serializers.ChoiceField(choices=ROLES, required=False)

    # ---- Campos de PACIENTE ----
    carnetidentidad = serializers.CharField(max_length=50, required=False, allow_blank=True)
    fechanacimiento = serializers.DateField(required=False, allow_null=True)
    direccion = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Rol por defecto: paciente
        rol = (attrs.get("rol") or "paciente").strip().lower()

        # Derivar idtipousuario si no viene (solo si tenemos mapping)
        derived_idtu = ROLE_TO_TU.get(rol)
        if not attrs.get("idtipousuario") and derived_idtu is not None:
            attrs["idtipousuario"] = derived_idtu

        # Si viene idtipousuario y también rol, exigir coherencia (si hay mapping)
        if derived_idtu is not None and attrs.get("idtipousuario") != derived_idtu:
            raise serializers.ValidationError({
                "idtipousuario": "No coincide con el rol indicado."
            })

        # Reglas por subtipo: paciente
        if rol == "paciente":
            faltan = []
            if not attrs.get("sexo"):
                faltan.append("sexo")
            if not attrs.get("direccion"):
                faltan.append("direccion")
            if not attrs.get("fechanacimiento"):
                faltan.append("fechanacimiento")
            if not attrs.get("carnetidentidad"):
                faltan.append("carnetidentidad")

            if faltan:
                raise serializers.ValidationError(
                    {"detail": f"Faltan campos de paciente: {', '.join(faltan)}"}
                )

            # Normaliza CI y valida unicidad
            ci = (attrs.get("carnetidentidad") or "").strip().upper()
            attrs["carnetidentidad"] = ci

            if ci and Paciente.objects.filter(carnetidentidad=ci).exists():
                raise serializers.ValidationError({"carnetidentidad": "El carnet ya existe."})

            # Fecha de nacimiento no futura
            from datetime import date
            if attrs.get("fechanacimiento") and attrs["fechanacimiento"] > date.today():
                raise serializers.ValidationError({"fechanacimiento": "No puede ser futura."})

        return attrs


# ============================
# Recuperar contraseña
# ============================

class ForgotPasswordRequestSerializer(serializers.Serializer):
    """
    Acepta email o username/registro en un solo campo 'identifier'.
    """
    identifier = serializers.CharField(
        max_length=254,
        allow_blank=False,
        trim_whitespace=True
    )


class ResetPasswordConfirmSerializer(serializers.Serializer):
    """
    Recibe uid + token del enlace y la nueva contraseña.
    """
    uid = serializers.CharField(allow_blank=False)
    token = serializers.CharField(allow_blank=False)
    new_password = serializers.CharField(
        min_length=8,
        write_only=True,
        allow_blank=False,
        style={"input_type": "password"}
    )
