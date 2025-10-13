# api/services/notification_service.py
from api.notifications_mobile.config import get_fcm_project_id, get_fcm_sa_info
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template import Template, Context
from django.utils import timezone
import requests
import json

from ..models import Usuario
from ..models_notifications import (
    TipoNotificacion, CanalNotificacion, PreferenciaNotificacion,
    DispositivoMovil, HistorialNotificacion, PlantillaNotificacion
)
logger = logging.getLogger(__name__)
from api.notifications_mobile.utils import mobile_send_push_fcm



class NotificationService:
    """
    Servicio centralizado para el manejo de notificaciones
    Adaptado para funcionar con Supabase en lugar de Firebase
    """

    def __init__(self):
        # Para push notifications, puedes usar OneSignal, Expo, o Supabase Edge Functions
        self.onesignal_app_id = getattr(settings, 'ONESIGNAL_APP_ID', None)
        self.onesignal_rest_key = getattr(settings, 'ONESIGNAL_REST_API_KEY', None)
        self.expo_access_token = getattr(settings, 'EXPO_ACCESS_TOKEN', None)
        self.supabase_edge_url = getattr(settings, 'SUPABASE_EDGE_FUNCTION_URL', None)
        self.fcm_project_id = get_fcm_project_id()
        self.fcm_sa_json = get_fcm_sa_info()

    def enviar_notificacion(
            self,
            usuarios: List[Usuario],
            tipo_notificacion_nombre: str,
            titulo: str,
            mensaje: str,
            canales: Optional[List[str]] = None,
            datos_adicionales: Optional[Dict[str, Any]] = None,
            usar_plantilla: bool = True
    ) -> Dict[str, Any]:
        """
        Envía notificaciones a una lista de usuarios
        """

        resultados = {
            'total_usuarios': len(usuarios),
            'enviados': 0,
            'errores': 0,
            'detalles': []
        }

        try:
            tipo_notificacion = TipoNotificacion.objects.get(nombre=tipo_notificacion_nombre, activo=True)
        except TipoNotificacion.DoesNotExist:
            logger.error(f"Tipo de notificación '{tipo_notificacion_nombre}' no encontrado")
            return resultados

        for usuario in usuarios:
            try:
                resultado_usuario = self._enviar_a_usuario(
                    usuario=usuario,
                    tipo_notificacion=tipo_notificacion,
                    titulo=titulo,
                    mensaje=mensaje,
                    canales=canales,
                    datos_adicionales=datos_adicionales,
                    usar_plantilla=usar_plantilla
                )

                if resultado_usuario['exito']:
                    resultados['enviados'] += 1
                else:
                    resultados['errores'] += 1

                resultados['detalles'].append({
                    'usuario_id': usuario.codigo,
                    'usuario_email': usuario.correoelectronico,
                    'exito': resultado_usuario['exito'],
                    'canales_enviados': resultado_usuario['canales_enviados'],
                    'errores': resultado_usuario['errores']
                })

            except Exception as e:
                logger.error(f"Error enviando notificación a usuario {usuario.codigo}: {str(e)}")
                resultados['errores'] += 1
                resultados['detalles'].append({
                    'usuario_id': usuario.codigo,
                    'usuario_email': usuario.correoelectronico,
                    'exito': False,
                    'canales_enviados': [],
                    'errores': [str(e)]
                })

        return resultados

    def _enviar_a_usuario(
            self,
            usuario: Usuario,
            tipo_notificacion: TipoNotificacion,
            titulo: str,
            mensaje: str,
            canales: Optional[List[str]],
            datos_adicionales: Optional[Dict[str, Any]],
            usar_plantilla: bool
    ) -> Dict[str, Any]:
        """
        Envía notificación a un usuario específico
        """

        resultado = {
            'exito': False,
            'canales_enviados': [],
            'errores': []
        }

        # Determinar canales a usar
        if canales is None:
            canales_activos = self._obtener_canales_activos(usuario, tipo_notificacion)
        else:
            canales_activos = self._filtrar_canales_por_preferencias(usuario, tipo_notificacion, canales)

        if not canales_activos:
            resultado['errores'].append("Usuario no tiene canales activos para este tipo de notificación")
            return resultado

        # Procesar plantillas si está habilitado
        if usar_plantilla:
            plantillas = self._obtener_plantillas(tipo_notificacion, canales_activos)
        else:
            plantillas = {}

        # Enviar por cada canal
        for canal in canales_activos:
            try:
                # Usar plantilla si está disponible
                if canal in plantillas:
                    plantilla = plantillas[canal]
                    titulo_final = self._procesar_plantilla(plantilla.titulo_template, usuario, datos_adicionales)
                    mensaje_final = self._procesar_plantilla(plantilla.mensaje_template, usuario, datos_adicionales)
                    asunto = self._procesar_plantilla(plantilla.asunto_template or titulo, usuario, datos_adicionales)
                else:
                    titulo_final = titulo
                    mensaje_final = mensaje
                    asunto = titulo

                # Registrar en historial
                historial = HistorialNotificacion.objects.create(
                    usuario=usuario,
                    tipo_notificacion=tipo_notificacion,
                    canal_notificacion=CanalNotificacion.objects.get(nombre=canal),
                    titulo=titulo_final,
                    mensaje=mensaje_final,
                    datos_adicionales=datos_adicionales or {},
                    estado='pendiente'
                )

                # Enviar según el canal
                if canal == 'email':
                    exito = self._enviar_email(usuario, asunto, titulo_final, mensaje_final, historial)
                elif canal == 'push':
                    exito = self._enviar_push(usuario, titulo_final, mensaje_final, datos_adicionales, historial)
                else:
                    exito = False
                    historial.error_mensaje = f"Canal '{canal}' no implementado"

                if exito:
                    resultado['canales_enviados'].append(canal)
                    historial.estado = 'enviado'
                    historial.fecha_envio = timezone.now()
                else:
                    resultado['errores'].append(f"Error enviando por {canal}")
                    historial.estado = 'error'

                historial.save()

            except Exception as e:
                logger.error(f"Error enviando por canal {canal} a usuario {usuario.codigo}: {str(e)}")
                resultado['errores'].append(f"Error en canal {canal}: {str(e)}")

        resultado['exito'] = len(resultado['canales_enviados']) > 0
        return resultado

    def _obtener_canales_activos(self, usuario: Usuario, tipo_notificacion: TipoNotificacion) -> List[str]:
        """
        Obtiene los canales activos para un usuario y tipo de notificación
        """
        preferencias = PreferenciaNotificacion.objects.filter(
            usuario=usuario,
            tipo_notificacion=tipo_notificacion,
            activo=True,
            canal_notificacion__activo=True
        ).select_related('canal_notificacion')

        return [pref.canal_notificacion.nombre for pref in preferencias]

    def _filtrar_canales_por_preferencias(
            self,
            usuario: Usuario,
            tipo_notificacion: TipoNotificacion,
            canales: List[str]
    ) -> List[str]:
        """
        Filtra canales según las preferencias del usuario
        """
        canales_activos = self._obtener_canales_activos(usuario, tipo_notificacion)
        return [canal for canal in canales if canal in canales_activos]

    def _obtener_plantillas(self, tipo_notificacion: TipoNotificacion, canales: List[str]) -> Dict[
        str, PlantillaNotificacion]:
        """
        Obtiene las plantillas para los canales especificados
        """
        plantillas = PlantillaNotificacion.objects.filter(
            tipo_notificacion=tipo_notificacion,
            canal_notificacion__nombre__in=canales,
            activo=True
        ).select_related('canal_notificacion')

        return {p.canal_notificacion.nombre: p for p in plantillas}

    def _procesar_plantilla(self, template_str: str, usuario: Usuario,
                            datos_adicionales: Optional[Dict[str, Any]]) -> str:
        """
        Procesa una plantilla con las variables del usuario y datos adicionales
        """
        if not template_str:
            return ""

        # Información de la clínica desde settings
        clinic_info = getattr(settings, 'CLINIC_INFO', {})

        context_data = {
            'usuario': usuario,
            'nombre': usuario.nombre,
            'apellido': usuario.apellido,
            'email': usuario.correoelectronico,
            'telefono': usuario.telefono,
            'fecha_actual': timezone.now().strftime('%d/%m/%Y'),
            'hora_actual': timezone.now().strftime('%H:%M'),
            'clinica_nombre': clinic_info.get('name', 'Clínica Dental'),
            'clinica_telefono': clinic_info.get('phone', ''),
            'clinica_email': clinic_info.get('email', ''),
            'clinica_direccion': clinic_info.get('address', ''),
        }

        if datos_adicionales:
            context_data.update(datos_adicionales)

        try:
            template = Template(template_str)
            context = Context(context_data)
            return template.render(context)
        except Exception as e:
            logger.error(f"Error procesando plantilla: {str(e)}")
            return template_str

    def _enviar_email(self, usuario: Usuario, asunto: str, titulo: str, mensaje: str,
                      historial: HistorialNotificacion) -> bool:
        """
        Envía notificación por email usando tu configuración actual
        """
        try:
            # Información de la clínica
            clinic_info = getattr(settings, 'CLINIC_INFO', {})

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{titulo}</title>
            </head>
            <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">

                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 24px; font-weight: normal;">{titulo}</h1>
                    </div>

                    <!-- Content -->
                    <div style="padding: 30px;">
                        <p style="color: #333; line-height: 1.6; margin-bottom: 20px; font-size: 16px;">
                            Hola <strong>{usuario.nombre}</strong>,
                        </p>

                        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; margin: 20px 0;">
                            <p style="color: #555; line-height: 1.6; margin: 0; font-size: 15px;">{mensaje.replace(chr(10), '<br>')}</p>
                        </div>

                        <div style="margin: 30px 0; text-align: center;">
                            <a href="{settings.FRONTEND_URL}" 
                               style="background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                                Ver en el Sistema
                            </a>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                        <p style="color: #6c757d; font-size: 14px; margin: 5px 0;">
                            <strong>{clinic_info.get('name', 'Clínica Dental')}</strong>
                        </p>
                        <p style="color: #6c757d; font-size: 13px; margin: 5px 0;">
                            📍 {clinic_info.get('address', 'Santa Cruz, Bolivia')} | 
                            📞 {clinic_info.get('phone', '')} | 
                            📧 {clinic_info.get('email', '')}
                        </p>
                        <p style="color: #adb5bd; font-size: 12px; margin: 15px 0 0 0;">
                            Puedes cambiar tus preferencias de notificación en tu perfil.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            text_content = f"""
{titulo}

Hola {usuario.nombre},

{mensaje}

---
{clinic_info.get('name', 'Clínica Dental')}
{clinic_info.get('address', 'Santa Cruz, Bolivia')}
{clinic_info.get('phone', '')}
{clinic_info.get('email', '')}

Puedes cambiar tus preferencias de notificación en: {settings.FRONTEND_URL}
            """

            email = EmailMultiAlternatives(
                subject=asunto,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[usuario.correoelectronico]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Email enviado exitosamente a {usuario.correoelectronico}")
            return True

        except Exception as e:
            logger.error(f"Error enviando email a {usuario.correoelectronico}: {str(e)}")
            historial.error_mensaje = str(e)
            return False

    def _enviar_push(
            self,
            usuario: Usuario,
            titulo: str,
            mensaje: str,
            datos_adicionales: Optional[Dict[str, Any]],
            historial: HistorialNotificacion
    ) -> bool:
        """
        Envía notificación push usando el primer proveedor disponible:
        OneSignal → Expo → Supabase → FCM (HTTP v1).
        """
        # Dispositivos activos del usuario
        dispositivos = DispositivoMovil.objects.filter(usuario=usuario, activo=True)

        if not dispositivos.exists():
            logger.warning(f"Usuario {usuario.codigo} no tiene dispositivos móviles registrados")
            historial.error_mensaje = "No hay dispositivos móviles registrados"
            return False

        # Proveedores (orden de prioridad)
        if self.onesignal_app_id and self.onesignal_rest_key:
            return self._enviar_push_onesignal(dispositivos, titulo, mensaje, datos_adicionales, historial)

        if self.expo_access_token:
            return self._enviar_push_expo(dispositivos, titulo, mensaje, datos_adicionales, historial)

        if self.supabase_edge_url:
            return self._enviar_push_supabase(dispositivos, titulo, mensaje, datos_adicionales, historial)

        # 🔹 FCM HTTP v1 como fallback
        if self.fcm_project_id and self.fcm_sa_json:
            tokens = [d.token_fcm for d in dispositivos if d.token_fcm]
            return self._enviar_push_fcm(tokens, titulo, mensaje, datos_adicionales, historial)

        # Si no hay ningún proveedor configurado
        logger.error("No hay servicio de push notifications configurado")
        historial.error_mensaje = "No hay servicio de push notifications configurado"
        return False


    def _enviar_push_fcm(
            self,
            tokens: List[str],
            titulo: str,
            mensaje: str,
            datos_adicionales: Optional[Dict[str, Any]],
            historial: HistorialNotificacion
    ) -> bool:
        """
        Envío de push con Firebase Cloud Messaging (HTTP v1) usando el submódulo notifications_mobile.
        No colisiona con el resto de canales.
        """
        try:
            if not self.fcm_project_id or not self.fcm_sa_json:
                historial.error_mensaje = "FCM no configurado (faltan FCM_PROJECT_ID o FCM_SERVICE_ACCOUNT_JSON)"
                return False

            tokens_validos = [t for t in tokens if t]
            if not tokens_validos:
                historial.error_mensaje = "No hay tokens FCM válidos"
                return False

            result = mobile_send_push_fcm(
                tokens=tokens_validos,
                title=titulo,
                body=mensaje,
                data=datos_adicionales or {},
                android_channel_id="smilestudio_default",
            )

            if result.get("sent", 0) > 0 and not result.get("errors"):
                return True

            errores = "; ".join(result.get("errors", []))[:500]
            historial.error_mensaje = f"FCM errors: {errores}" if errores else "FCM no envió mensajes"
            return result.get("sent", 0) > 0

        except Exception as e:
            historial.error_mensaje = f"FCM exception: {str(e)}"
            return False


    def _enviar_push_onesignal(
            self,
            dispositivos,
            titulo: str,
            mensaje: str,
            datos_adicionales: Optional[Dict[str, Any]],
            historial: HistorialNotificacion
    ) -> bool:
        """
        Envía push notification usando OneSignal
        """
        try:
            # Obtener tokens de los dispositivos
            player_ids = [d.token_fcm for d in dispositivos if d.token_fcm]

            if not player_ids:
                historial.error_mensaje = "No hay tokens válidos de OneSignal"
                return False

            payload = {
                "app_id": self.onesignal_app_id,
                "include_player_ids": player_ids,
                "headings": {"en": titulo, "es": titulo},
                "contents": {"en": mensaje, "es": mensaje},
                "data": datos_adicionales or {},
                "android_sound": "default",
                "ios_sound": "default"
            }

            headers = {
                "Authorization": f"Basic {self.onesignal_rest_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://onesignal.com/api/v1/notifications",
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )

            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Push OneSignal enviado: {response_data.get('recipients', 0)} recipients")
                return True
            else:
                error_msg = f"OneSignal error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                historial.error_mensaje = error_msg
                return False

        except Exception as e:
            logger.error(f"Error enviando push OneSignal: {str(e)}")
            historial.error_mensaje = str(e)
            return False

    def _enviar_push_expo(
            self,
            dispositivos,
            titulo: str,
            mensaje: str,
            datos_adicionales: Optional[Dict[str, Any]],
            historial: HistorialNotificacion
    ) -> bool:
        """
        Envía push notification usando Expo Push Service
        """
        try:
            expo_tokens = [d.token_fcm for d in dispositivos if d.token_fcm.startswith('ExponentPushToken')]

            if not expo_tokens:
                historial.error_mensaje = "No hay tokens válidos de Expo"
                return False

            messages = []
            for token in expo_tokens:
                messages.append({
                    "to": token,
                    "title": titulo,
                    "body": mensaje,
                    "data": datos_adicionales or {},
                    "sound": "default",
                    "badge": 1
                })

            headers = {
                "Authorization": f"Bearer {self.expo_access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://exp.host/--/api/v2/push/send",
                headers=headers,
                data=json.dumps(messages),
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Push Expo enviado a {len(messages)} dispositivos")
                return True
            else:
                error_msg = f"Expo error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                historial.error_mensaje = error_msg
                return False

        except Exception as e:
            logger.error(f"Error enviando push Expo: {str(e)}")
            historial.error_mensaje = str(e)
            return False

    def _enviar_push_supabase(
            self,
            dispositivos,
            titulo: str,
            mensaje: str,
            datos_adicionales: Optional[Dict[str, Any]],
            historial: HistorialNotificacion
    ) -> bool:
        """
        Envía push notification usando Supabase Edge Function
        """
        try:
            tokens = [d.token_fcm for d in dispositivos if d.token_fcm]

            if not tokens:
                historial.error_mensaje = "No hay tokens válidos"
                return False

            payload = {
                "tokens": tokens,
                "title": titulo,
                "body": mensaje,
                "data": datos_adicionales or {}
            }

            headers = {
                "Authorization": f"Bearer {getattr(settings, 'SUPABASE_ANON_KEY', '')}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.supabase_edge_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Push Supabase enviado a {len(tokens)} dispositivos")
                return True
            else:
                error_msg = f"Supabase Edge Function error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                historial.error_mensaje = error_msg
                return False

        except Exception as e:
            logger.error(f"Error enviando push Supabase: {str(e)}")
            historial.error_mensaje = str(e)
            return False

    def registrar_dispositivo_movil(
            self,
            usuario: Usuario,
            token_fcm: str,
            plataforma: str,
            modelo_dispositivo: str = None,
            version_app: str = None
    ) -> DispositivoMovil:
        """
        Registra un nuevo dispositivo móvil o actualiza uno existente
        """
        dispositivo, created = DispositivoMovil.objects.update_or_create(
            token_fcm=token_fcm,
            defaults={
                'usuario': usuario,
                'plataforma': plataforma,
                'modelo_dispositivo': modelo_dispositivo,
                'version_app': version_app,
                'activo': True,
                'ultima_actividad': timezone.now()
            }
        )

        if created:
            logger.info(f"Nuevo dispositivo registrado para usuario {usuario.codigo}")
        else:
            logger.info(f"Dispositivo actualizado para usuario {usuario.codigo}")

        return dispositivo

    def obtener_preferencias_usuario(self, usuario: Usuario) -> Dict[str, Any]:
        """
        Obtiene todas las preferencias de notificación de un usuario
        """
        preferencias = PreferenciaNotificacion.objects.filter(
            usuario=usuario
        ).select_related('tipo_notificacion', 'canal_notificacion')

        # Organizar preferencias por tipo y canal
        prefs_dict = {}
        for pref in preferencias:
            tipo_key = f"{pref.tipo_notificacion.nombre.lower().replace(' ', '_')}_{pref.canal_notificacion.nombre}"
            prefs_dict[tipo_key] = pref.activo

        # Dispositivos móviles
        dispositivos = DispositivoMovil.objects.filter(usuario=usuario, activo=True)

        return {
            'usuario_id': usuario.codigo,
            'email_activo': any(p.activo for p in preferencias if p.canal_notificacion.nombre == 'email'),
            'push_activo': any(p.activo for p in preferencias if p.canal_notificacion.nombre == 'push'),
            'preferencias': prefs_dict,
            'dispositivos_moviles': [
                {
                    'id': d.id,
                    'plataforma': d.plataforma,
                    'modelo_dispositivo': d.modelo_dispositivo,
                    'version_app': d.version_app,
                    'fecha_registro': d.fecha_registro,
                    'ultima_actividad': d.ultima_actividad
                }
                for d in dispositivos
            ]
        }

    def actualizar_preferencias_usuario(self, usuario: Usuario, preferencias: Dict[str, bool]) -> Dict[str, Any]:
        """
        Actualiza las preferencias de notificación de un usuario
        """
        actualizadas = 0
        errores = []

        # Mapeo de campos del serializer a tipo_notificacion + canal
        mapeo_preferencias = {
            'cita_recordatorio_email': ('Recordatorio de Cita', 'email'),
            'cita_recordatorio_push': ('Recordatorio de Cita', 'push'),
            'cita_confirmacion_email': ('Confirmación de Cita', 'email'),
            'cita_confirmacion_push': ('Confirmación de Cita', 'push'),
            'cita_cancelacion_email': ('Cancelación de Cita', 'email'),
            'cita_cancelacion_push': ('Cancelación de Cita', 'push'),
            'reagendamiento_email': ('Reagendamiento de Cita', 'email'),
            'reagendamiento_push': ('Reagendamiento de Cita', 'push'),
            'resultado_disponible_email': ('Resultado Disponible', 'email'),
            'resultado_disponible_push': ('Resultado Disponible', 'push'),
            'factura_generada_email': ('Factura Generada', 'email'),
            'factura_generada_push': ('Factura Generada', 'push'),
            'pago_confirmado_email': ('Pago Confirmado', 'email'),
            'pago_confirmado_push': ('Pago Confirmado', 'push'),
            'pago_vencido_email': ('Pago Vencido', 'email'),
            'pago_vencido_push': ('Pago Vencido', 'push'),
            'plan_tratamiento_email': ('Plan de Tratamiento', 'email'),
            'plan_tratamiento_push': ('Plan de Tratamiento', 'push'),
            'sistema_email': ('Sistema', 'email'),
            'sistema_push': ('Sistema', 'push'),
            'promociones_email': ('Promociones', 'email'),
            'promociones_push': ('Promociones', 'push'),
        }

        for pref_key, activo in preferencias.items():
            if pref_key in mapeo_preferencias:
                tipo_nombre, canal_nombre = mapeo_preferencias[pref_key]

                try:
                    tipo_notificacion = TipoNotificacion.objects.get(nombre=tipo_nombre)
                    canal_notificacion = CanalNotificacion.objects.get(nombre=canal_nombre)

                    pref, created = PreferenciaNotificacion.objects.update_or_create(
                        usuario=usuario,
                        tipo_notificacion=tipo_notificacion,
                        canal_notificacion=canal_notificacion,
                        defaults={'activo': activo}
                    )

                    actualizadas += 1

                except (TipoNotificacion.DoesNotExist, CanalNotificacion.DoesNotExist) as e:
                    errores.append(f"Error en {pref_key}: {str(e)}")

        return {
            'actualizadas': actualizadas,
            'errores': errores,
            'total_procesadas': len(preferencias)
        }

    def marcar_notificacion_como_leida(self, notificacion_id: int, usuario: Usuario) -> bool:
        """
        Marca una notificación como leída
        """
        try:
            notificacion = HistorialNotificacion.objects.get(
                id=notificacion_id,
                usuario=usuario
            )
            notificacion.estado = 'leido'
            notificacion.fecha_lectura = timezone.now()
            notificacion.save()

            logger.info(f"Notificación {notificacion_id} marcada como leída")
            return True

        except HistorialNotificacion.DoesNotExist:
            logger.error(f"Notificación {notificacion_id} no encontrada para usuario {usuario.codigo}")
            return False

    def obtener_historial_notificaciones(
            self,
            usuario: Usuario,
            limite: int = 50,
            solo_no_leidas: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de notificaciones de un usuario
        """
        queryset = HistorialNotificacion.objects.filter(
            usuario=usuario
        ).select_related('tipo_notificacion', 'canal_notificacion').order_by('-fecha_creacion')

        if solo_no_leidas:
            queryset = queryset.exclude(estado='leido')

        notificaciones = queryset[:limite]

        return [
            {
                'id': n.id,
                'tipo': n.tipo_notificacion.nombre,
                'canal': n.canal_notificacion.get_nombre_display(),
                'titulo': n.titulo,
                'mensaje': n.mensaje,
                'estado': n.estado,
                'fecha_creacion': n.fecha_creacion,
                'fecha_envio': n.fecha_envio,
                'fecha_lectura': n.fecha_lectura,
                'datos_adicionales': n.datos_adicionales
            }
            for n in notificaciones
        ]

    def crear_tipos_notificacion_default(self):
        """
        Crea los tipos de notificación por defecto si no existen
        """
        tipos_default = [
            {
                'nombre': 'Recordatorio de Cita',
                'descripcion': 'Recordatorio enviado antes de una cita programada'
            },
            {
                'nombre': 'Confirmación de Cita',
                'descripcion': 'Confirmación cuando se agenda una nueva cita'
            },
            {
                'nombre': 'Cancelación de Cita',
                'descripcion': 'Notificación cuando se cancela una cita'
            },
            {
                'nombre': 'Reagendamiento de Cita',
                'descripcion': 'Notificación cuando se reagenda una cita'
            },
            {
                'nombre': 'Resultado Disponible',
                'descripcion': 'Notificación cuando están disponibles resultados de estudios'
            },
            {
                'nombre': 'Factura Generada',
                'descripcion': 'Notificación cuando se genera una nueva factura'
            },
            {
                'nombre': 'Pago Confirmado',
                'descripcion': 'Confirmación cuando se recibe un pago'
            },
            {
                'nombre': 'Pago Vencido',
                'descripcion': 'Notificación cuando un pago está vencido'
            },
            {
                'nombre': 'Plan de Tratamiento',
                'descripcion': 'Notificaciones relacionadas con planes de tratamiento'
            },
            {
                'nombre': 'Sistema',
                'descripcion': 'Notificaciones generales del sistema'
            },
            {
                'nombre': 'Promociones',
                'descripcion': 'Ofertas y promociones especiales'
            }
        ]

        for tipo_data in tipos_default:
            TipoNotificacion.objects.get_or_create(
                nombre=tipo_data['nombre'],
                defaults={'descripcion': tipo_data['descripcion']}
            )

        # Crear canales por defecto
        canales_default = [
            ('email', 'Correo Electrónico'),
            ('push', 'Notificación Push'),
        ]

        for canal_nombre, canal_descripcion in canales_default:
            CanalNotificacion.objects.get_or_create(
                nombre=canal_nombre,
                defaults={'descripcion': canal_descripcion}
            )

        logger.info("Tipos y canales de notificación por defecto creados")

    def enviar_recordatorios_citas(self, horas_antes: int = 24):
        """
        Envía recordatorios de citas programadas
        """
        from datetime import timedelta
        from ..models import Consulta

        # Calcular fecha objetivo
        fecha_recordatorio = timezone.now().date() + timedelta(hours=horas_antes)

        # Obtener citas que necesitan recordatorio
        citas = Consulta.objects.filter(
            fecha=fecha_recordatorio,
            idestadoconsulta__estado__in=['Confirmada', 'Programada']
        ).select_related(
            'codpaciente__codusuario',
            'cododontologo__codusuario',
            'idhorario',
            'idtipoconsulta'
        )

        recordatorios_enviados = 0
        errores = 0

        for cita in citas:
            try:
                resultado = self.enviar_notificacion(
                    usuarios=[cita.codpaciente.codusuario],
                    tipo_notificacion_nombre='Recordatorio de Cita',
                    titulo='Recordatorio: Tienes una cita mañana',
                    mensaje=f'Te recordamos tu cita dental programada para mañana {cita.fecha.strftime("%d/%m/%Y")} a las {cita.idhorario.hora.strftime("%H:%M")}.',
                    datos_adicionales={
                        'cita_id': cita.id,
                        'fecha': cita.fecha.strftime('%d/%m/%Y'),
                        'hora': cita.idhorario.hora.strftime('%H:%M'),
                        'doctor': cita.cododontologo.codusuario.nombre if cita.cododontologo else 'Por asignar',
                        'tipo_consulta': cita.idtipoconsulta.nombreconsulta,
                        'ubicacion': getattr(settings, 'CLINIC_INFO', {}).get('address', 'Clínica Dental')
                    }
                )

                if resultado['enviados'] > 0:
                    recordatorios_enviados += 1
                else:
                    errores += 1

            except Exception as e:
                logger.error(f"Error enviando recordatorio para cita {cita.id}: {str(e)}")
                errores += 1

        logger.info(f"Recordatorios procesados: {recordatorios_enviados} enviados, {errores} errores")
        return {
            'enviados': recordatorios_enviados,
            'errores': errores,
            'total_citas': citas.count()
        }


# Instancia global del servicio..
notification_service = NotificationService()