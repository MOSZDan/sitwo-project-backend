# api/notifications_mobile/views.py
"""
Views opcionales namespaced 'mobile-*'. Solo se activan si incluyes
api.notifications_mobile.urls en tu árbol. No interfieren con api existente.
"""
from __future__ import annotations

import logging
import os

from django.db import transaction
from django.utils import timezone
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.authentication import TokenAuthentication

from .serializers import (
    MobileRegisterDeviceSerializerLite,
    MobileRegisterDeviceSerializer,
)
from .utils import mobile_send_push_fcm, mobile_notifications_health
from .models import UsuarioMN, DispositivoMovilMN, HistorialNotificacionMN

logger = logging.getLogger(__name__)

# Secreto para el dispatcher (puedes setear NOTIF_DISPATCH_SECRET en el entorno)
NOTIF_DISPATCH_SECRET = os.environ.get("NOTIF_DISPATCH_SECRET", "DEV_NOTIF_SECRET")


class MobileNotificationsHealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(mobile_notifications_health(), status=status.HTTP_200_OK)


class MobileNotificationsTestPushView(APIView):
    """
    Endpoint de prueba para enviar push a una lista de tokens (solo dev).
    No se carga si no incluyes estas urls.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        tokens = request.data.get("tokens") or []
        title = request.data.get("title") or "Test"
        body = request.data.get("body") or "Hello from mobile-notifications"
        data = request.data.get("data") or {}
        result = mobile_send_push_fcm(tokens, title, body, data)
        return Response(result, status=status.HTTP_200_OK)


class MobileRegisterDeviceLiteView(APIView):
    """
    Registro de dispositivo alternativo (lite). Útil para pruebas rápidas.
    No toca tus modelos ni rutas actuales (no persiste).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = MobileRegisterDeviceSerializerLite(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response({"ok": True, "received": ser.validated_data}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class MobileRegisterDeviceView(APIView):
    """
    Upsert de dispositivo en BD (clave por usuario).
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = MobileRegisterDeviceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        auth_user = request.user
        email = getattr(auth_user, "email", None) or getattr(auth_user, "username", None)
        if not email:
            return Response({"ok": False, "detail": "Usuario sin email/username"}, status=status.HTTP_400_BAD_REQUEST)

        u = UsuarioMN.objects.filter(correoelectronico__iexact=email).order_by("codigo").first()
        if not u:
            return Response({"ok": False, "detail": "Usuario de negocio no encontrado"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        plataforma = (data.get("plataforma") or "").strip().lower()
        modelo = (data.get("modelo_dispositivo") or "").strip()
        version_app = (data.get("version_app") or "").strip()

        if not modelo:
            modelo = (
                request.headers.get("X-Device-Model")
                or request.META.get("HTTP_X_DEVICE_MODEL")
                or request.META.get("HTTP_USER_AGENT")
                or "unknown"
            )
            modelo = str(modelo)[:100]

        created = False
        with transaction.atomic():
            token = data["token_fcm"].strip()
            created = False

            # 1) ¿Existe YA ese token en cualquier registro?
            d = (
                DispositivoMovilMN.objects
                .select_for_update()
                .filter(token_fcm=token)
                .order_by("id")
                .first()
            )

            if d:
                # Reasignar al usuario actual y actualizar campos
                updates = []
                if d.codusuario != u.codigo:
                    d.codusuario = u.codigo; updates.append("codusuario")
                if plataforma and d.plataforma != plataforma:
                    d.plataforma = plataforma; updates.append("plataforma")
                if modelo and (d.modelo_dispositivo or "") != modelo:
                    d.modelo_dispositivo = modelo; updates.append("modelo_dispositivo")
                if version_app and (d.version_app or "") != version_app:
                    d.version_app = version_app; updates.append("version_app")
                if not d.activo:
                    d.activo = True; updates.append("activo")
                d.ultima_actividad = now; updates.append("ultima_actividad")
                if updates:
                    d.save(update_fields=updates)
            else:
                # 2) No existe el token: reciclar el primer dispositivo del usuario o crear uno nuevo
                d = (
                    DispositivoMovilMN.objects
                    .select_for_update()
                    .filter(codusuario=u.codigo)
                    .order_by("id")
                    .first()
                )
                if d:
                    updates = []
                    if d.token_fcm != token:
                        d.token_fcm = token; updates.append("token_fcm")
                    if plataforma and d.plataforma != plataforma:
                        d.plataforma = plataforma; updates.append("plataforma")
                    if modelo and (d.modelo_dispositivo or "") != modelo:
                        d.modelo_dispositivo = modelo; updates.append("modelo_dispositivo")
                    if version_app and (d.version_app or "") != version_app:
                        d.version_app = version_app; updates.append("version_app")
                    if not d.activo:
                        d.activo = True; updates.append("activo")
                    d.ultima_actividad = now; updates.append("ultima_actividad")
                    if updates:
                        d.save(update_fields=updates)
                else:
                    d = DispositivoMovilMN.objects.create(
                        token_fcm=token,
                        plataforma=plataforma or "android",
                        modelo_dispositivo=modelo,
                        version_app=version_app or None,
                        activo=True,
                        fecha_registro=now,
                        ultima_actividad=now,
                        codusuario=u.codigo,
                    )
                    created = True

            # 3) Desactivar otros dispositivos del mismo usuario
            DispositivoMovilMN.objects.filter(codusuario=u.codigo).exclude(id=d.id).update(activo=False)

        payload = {
            "ok": True,
            "created": created,
            "device_id": d.id,
            "usuario_codigo": u.codigo,
            "plataforma": d.plataforma,
            "modelo_dispositivo": d.modelo_dispositivo,
            "version_app": d.version_app,
        }
        logger.debug("MobileRegisterDeviceView result: %s", payload)
        return Response(payload, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def mobile_dispatch_notification(request, pk: int):
    """
    Ejecuta una notificación PENDIENTE (si fecha_envio <= now).
    """
    obj = HistorialNotificacionMN.objects.filter(id=pk, estado="PENDIENTE").first()
    if not obj:
        return Response({"detail": "not-found-or-not-pending"}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()
    if obj.fecha_envio and obj.fecha_envio > now:
        return Response({"detail": "too-early"}, status=status.HTTP_202_ACCEPTED)

    data = obj.datos_adicionales or {}
    codusuario = obj.codusuario or data.get("paciente_codusuario")

    tokens = list(
        DispositivoMovilMN.objects.filter(codusuario=codusuario, activo=True)
        .exclude(token_fcm__isnull=True)
        .exclude(token_fcm="")
        .values_list("token_fcm", flat=True)
    )

    try:
        res = mobile_send_push_fcm(tokens, obj.titulo, obj.mensaje, data)
        HistorialNotificacionMN.objects.filter(id=obj.id).update(
            estado="ENVIADO",
            fecha_entrega=now,            # usamos como “enviado”
            intentos=F("intentos") + 1,
            error_mensaje="",
        )
        return Response({"sent_to": len(tokens), "res": res}, status=status.HTTP_200_OK)
    except Exception as e:
        HistorialNotificacionMN.objects.filter(id=obj.id).update(
            estado="ERROR",
            intentos=F("intentos") + 1,
            error_mensaje=str(e)[:1000],
        )
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- NUEVO: despachar todas las notificaciones vencidas en lote ---
@api_view(["POST"])
@permission_classes([AllowAny])
def mobile_dispatch_due(request):
    """
    Despacha hasta 200 notificaciones PENDIENTE con fecha_envio <= ahora.
    Sin secretos, sin auth, pensado para pruebas locales y para Lambda simple.
    """
    from django.utils import timezone
    from .models import HistorialNotificacionMN, DispositivoMovilMN
    from .utils import mobile_send_push_fcm

    now = timezone.now()
    # límite de 200 por tanda
    pendientes = (
        HistorialNotificacionMN.objects
        .filter(estado="PENDIENTE", fecha_envio__lte=now)
        .order_by("id")[:200]
    )

    total = pendientes.count()
    enviados = 0
    errores = 0
    procesados = []

    for obj in pendientes:
        data = obj.datos_adicionales or {}
        codusuario = obj.codusuario or data.get("paciente_codusuario")

        # 1 dispositivo activo por usuario (tu requerimiento)
        dev = (
            DispositivoMovilMN.objects
            .filter(codusuario=codusuario, activo=True)
            .exclude(token_fcm__isnull=True)
            .exclude(token_fcm="")
            .order_by("-ultima_actividad")
            .first()
        )
        tokens = [dev.token_fcm] if dev else []

        try:
            # Envía push (usa tus credenciales FCM existentes)
            mobile_send_push_fcm(tokens, obj.titulo, obj.mensaje, data)

            # Marca como ENVIADO y rellena iddispositivomovil si lo tenemos
            obj.estado = "ENVIADO"
            obj.fecha_entrega = now
            obj.intentos = (obj.intentos or 0) + 1
            obj.error_mensaje = ""
            if dev:
                obj.iddispositivomovil = dev.id
            obj.save(update_fields=[
                "estado", "fecha_entrega", "intentos", "error_mensaje", "iddispositivomovil"
            ])

            enviados += 1
            procesados.append(obj.id)
        except Exception as e:
            # Marca ERROR, guardando el último mensaje
            obj.estado = "ERROR"
            obj.intentos = (obj.intentos or 0) + 1
            obj.error_mensaje = str(e)[:1000]
            if dev:
                obj.iddispositivomovil = dev.id
            obj.save(update_fields=[
                "estado", "intentos", "error_mensaje", "iddispositivomovil"
            ])
            errores += 1
            procesados.append(obj.id)

    return Response({
        "total_due": total,
        "sent": enviados,
        "errors": errores,
        "processed_ids": procesados,
    }, status=status.HTTP_200_OK)


# --- NUEVO: Vista de clase para despacho en lote más robusta ---
from django.conf import settings

class MobileDispatchDueView(APIView):
    """
    Despacha en lote notificaciones PENDIENTES con fecha_envio <= ahora.
    - En DEBUG: no requiere auth.
    - En prod: si defines NOTIF_DISPATCH_SECRET, envía header X-Notif-Secret.
    Límite por corrida: ?max=200 (default 200).
    """
    permission_classes = [permissions.AllowAny]  # no CSRF para clientes server-to-server

    @method_decorator(csrf_exempt)
    def post(self, request):
        # seguridad simple: en prod, si hay secreto definido, verifica header
        secret_required = getattr(settings, "NOTIF_DISPATCH_SECRET", None)
        if not settings.DEBUG and secret_required:
            if request.headers.get("X-Notif-Secret") != secret_required:
                return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        try:
            max_count = int(request.query_params.get("max", "200"))
        except Exception:
            max_count = 200
        max_count = max(1, min(max_count, 500))  # hard cap 500

        now = timezone.now()
        qs = (
            HistorialNotificacionMN.objects
            .filter(estado="PENDIENTE", fecha_envio__lte=now)
            .order_by("id")[:max_count]
        )

        sent, errors = 0, 0
        results = []

        for obj in qs:
            data = obj.datos_adicionales or {}
            codusuario = obj.codusuario or data.get("paciente_codusuario")

            # único dispositivo activo -> resolvemos tokens y guardamos id
            device = (
                DispositivoMovilMN.objects
                .filter(codusuario=codusuario, activo=True)
                .order_by("-ultima_actividad")
                .first()
            )
            tokens = []
            if device and device.token_fcm:
                tokens = [device.token_fcm]

            try:
                res = mobile_send_push_fcm(tokens, obj.titulo, obj.mensaje, data)
                # marcamos como ENVIADO; guardamos iddispositivomovil que usamos
                HistorialNotificacionMN.objects.filter(id=obj.id).update(
                    estado="ENVIADO",
                    fecha_entrega=now,
                    intentos=F("intentos") + 1,
                    error_mensaje="",
                    iddispositivomovil=(device.id if device else None),
                )
                sent += 1
                results.append({"id": obj.id, "sent_to": len(tokens)})
            except Exception as e:
                HistorialNotificacionMN.objects.filter(id=obj.id).update(
                    estado="ERROR",
                    intentos=F("intentos") + 1,
                    error_mensaje=str(e)[:1000],
                    iddispositivomovil=(device.id if device else None),
                )
                errors += 1
                results.append({"id": obj.id, "error": str(e)})

        return Response(
            {"ok": True, "processed": len(qs), "sent": sent, "errors": errors, "items": results},
            status=status.HTTP_200_OK
        )
