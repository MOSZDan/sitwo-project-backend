# api/serializers_auth.py
from rest_framework import serializers
from .models import Paciente
import re

ROLES = ("paciente", "odontologo", "recepcionista")

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

    # Teléfono: opcional; si viene, exactamente 8 dígitos
    telefono = serializers.CharField(
        min_length=8,
        max_length=8,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "min_length": "Cantidad de dígitos de teléfono inválido",
            "max_length": "Cantidad de dígitos de teléfono inválido",
        },
    )
    sexo = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Catálogo/rol
    idtipousuario = serializers.IntegerField(required=False)
    rol = serializers.ChoiceField(choices=ROLES, required=False)

    # ---- Campos de PACIENTE ----
    # CI: para paciente es obligatorio; exactamente 8 dígitos
    carnetidentidad = serializers.CharField(
        min_length=8,
        max_length=8,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "min_length": "Cantidad de dígitos de carnet de identidad inválido",
            "max_length": "Cantidad de dígitos de carnet de identidad inválido",
        },
    )
    fechanacimiento = serializers.DateField(required=False, allow_null=True)
    direccion = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        # Recibir el request para obtener el tenant (multi-tenancy)
        self.request = kwargs.pop('context', {}).get('request', None)
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        # Rol por defecto: paciente
        rol = (attrs.get("rol") or "paciente").strip().lower()

        # Derivar idtipousuario si no viene (si hay mapping)
        derived_idtu = ROLE_TO_TU.get(rol)
        if not attrs.get("idtipousuario") and derived_idtu is not None:
            attrs["idtipousuario"] = derived_idtu

        # Coherencia entre idtipousuario y rol
        if derived_idtu is not None and attrs.get("idtipousuario") != derived_idtu:
            raise serializers.ValidationError({
                "idtipousuario": "No coincide con el rol indicado."
            })

        # --- Teléfono: opcional, pero si viene -> exactamente 8 dígitos ---
        tel = (attrs.get("telefono") or "").strip()
        if tel:
            if not re.fullmatch(r"\d{8}", tel):
                raise serializers.ValidationError({"telefono": "Cantidad de digitos telefónico inválido"})
            attrs["telefono"] = tel  # normalizado

        # --- Reglas por subtipo: paciente ---
        if rol == "paciente":
            faltan = []
            if not (attrs.get("sexo") or "").strip():
                faltan.append("sexo")
            if not (attrs.get("direccion") or "").strip():
                faltan.append("direccion")
            if not attrs.get("fechanacimiento"):
                faltan.append("fechanacimiento")

            ci = (attrs.get("carnetidentidad") or "").strip()
            if not ci:
                faltan.append("carnetidentidad")

            if faltan:
                raise serializers.ValidationError(
                    {"detail": f"Faltan campos de paciente: {', '.join(faltan)}"}
                )

            # CI: exactamente 8 dígitos
            if not re.fullmatch(r"\d{8}", ci):
                raise serializers.ValidationError({"carnetidentidad": "Cantidad de digitos de carnet de identidad inválido"})
            attrs["carnetidentidad"] = ci  # normalizado

            # Unicidad CI (POR EMPRESA en multi-tenancy)
            empresa = getattr(self.request, 'tenant', None) if self.request else None
            if empresa:
                # Validar CI único dentro de la empresa
                if Paciente.objects.filter(carnetidentidad=ci, empresa=empresa).exists():
                    raise serializers.ValidationError({"carnetidentidad": "El carnet ya existe en esta clínica."})
            else:
                # Sin tenant, validar globalmente (fallback para compatibilidad)
                if Paciente.objects.filter(carnetidentidad=ci).exists():
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
