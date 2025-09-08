# api/serializers_auth.py
from rest_framework import serializers
from .models import Paciente

# Mapeo oficial de tu catálogo:
# 1 = administrador, 2 = paciente, 3 = recepcionista, 4 = odontologo
ROLE_TO_TU = {
    "administrador": 1,
    "paciente": 2,
    "recepcionista": 3,
    "odontologo": 4,
}

# Aceptamos estos roles en el payload (compatibles con tu FE).
ROLES = ("paciente", "recepcionista", "odontologo", "administrador")

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

        # Derivar idtipousuario si no viene
        derived_idtu = ROLE_TO_TU.get(rol)
        if not attrs.get("idtipousuario"):
            attrs["idtipousuario"] = derived_idtu

        # Si viene idtipousuario y también rol, exigir coherencia
        if attrs.get("idtipousuario") != derived_idtu:
            raise serializers.ValidationError({
                "idtipousuario": "No coincide con el rol indicado."
            })

        # Reglas por subtipo: paciente
        if rol == "paciente":
            faltan = []
            for f in ("sexo", "direccion", "fechanacimiento", "carnetidentidad"):
                if not attrs.get(f):
                    faltan.append(f)
            if faltan:
                raise serializers.ValidationError({
                    "detail": f"Faltan campos de paciente: {', '.join(faltan)}"
                })

            # Normaliza CI y valida lógica mínima
            ci = (attrs.get("carnetidentidad") or "").strip().upper()
            attrs["carnetidentidad"] = ci

            # Fecha de nacimiento no futura
            from datetime import date
            if attrs.get("fechanacimiento") and attrs["fechanacimiento"] > date.today():
                raise serializers.ValidationError({"fechanacimiento": "No puede ser futura."})

        return attrs