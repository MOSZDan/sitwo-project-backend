# api/views_notifications.py
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Usuario
from .models_notifications import (
    TipoNotificacion, CanalNotificacion, PreferenciaNotificacion,
    DispositivoMovil, HistorialNotificacion, PlantillaNotificacion
)
from .serializers_notifications import (
    TipoNotificacionSerializer, CanalNotificacionSerializer,
    PreferenciaNotificacionSerializer, CreatePreferenciaNotificacionSerializer,
    DispositivoMovilSerializer, RegisterDispositivoMovilSerializer,
    HistorialNotificacionSerializer, PlantillaNotificacionSerializer,
    PreferenciasUsuarioSerializer, ActualizarPreferenciasSerializer,
    EnviarNotificacionSerializer
)
from .services.notification_service import notification_service


class TipoNotificacionViewSet(ReadOnlyModelViewSet):
    """
    ViewSet para consultar tipos de notificación disponibles
    """
    queryset = TipoNotificacion.objects.filter(activo=True)
    serializer_class = TipoNotificacionSerializer
    permission_classes = [IsAuthenticated]


class CanalNotificacionViewSet(ReadOnlyModelViewSet):
    """
    ViewSet para consultar canales de notificación disponibles
    """
    queryset = CanalNotificacion.objects.filter(activo=True)
    serializer_class = CanalNotificacionSerializer
    permission_classes = [IsAuthenticated]


class PreferenciaNotificacionViewSet(ModelViewSet):
    """
    ViewSet para gestionar preferencias de notificación individuales
    """
    serializer_class = PreferenciaNotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PreferenciaNotificacion.objects.filter(
            usuario__correoelectronico=self.request.user.email
        ).select_related('tipo_notificacion', 'canal_notificacion')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreatePreferenciaNotificacionSerializer
        return PreferenciaNotificacionSerializer

    def perform_create(self, serializer):
        try:
            usuario = Usuario.objects.get(correoelectronico=self.request.user.email)
            serializer.save(usuario=usuario)
        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado en el sistema"},
                status=status.HTTP_404_NOT_FOUND
            )


class DispositivoMovilViewSet(ModelViewSet):
    """
    ViewSet para gestionar dispositivos móviles del usuario
    """
    serializer_class = DispositivoMovilSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DispositivoMovil.objects.filter(
            usuario__correoelectronico=self.request.user.email,
            activo=True
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterDispositivoMovilSerializer
        return DispositivoMovilSerializer

    def perform_create(self, serializer):
        try:
            usuario = Usuario.objects.get(correoelectronico=self.request.user.email)

            # Usar el servicio para registrar el dispositivo
            dispositivo = notification_service.registrar_dispositivo_movil(
                usuario=usuario,
                token_fcm=serializer.validated_data['token_fcm'],
                plataforma=serializer.validated_data['plataforma'],
                modelo_dispositivo=serializer.validated_data.get('modelo_dispositivo'),
                version_app=serializer.validated_data.get('version_app')
            )

            # Retornar el dispositivo creado/actualizado
            return Response(
                DispositivoMovilSerializer(dispositivo).data,
                status=status.HTTP_201_CREATED
            )

        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado en el sistema"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        """
        Desactiva un dispositivo móvil
        """
        dispositivo = self.get_object()
        dispositivo.activo = False
        dispositivo.save()

        return Response(
            {"detail": "Dispositivo desactivado correctamente"},
            status=status.HTTP_200_OK
        )


class HistorialNotificacionViewSet(ReadOnlyModelViewSet):
    """
    ViewSet para consultar el historial de notificaciones del usuario
    """
    serializer_class = HistorialNotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = HistorialNotificacion.objects.filter(
            usuario__correoelectronico=self.request.user.email
        ).select_related(
            'tipo_notificacion', 'canal_notificacion', 'dispositivo_movil'
        ).order_by('-fecha_creacion')

        # Filtros opcionales
        solo_no_leidas = self.request.query_params.get('solo_no_leidas', 'false').lower() == 'true'
        if solo_no_leidas:
            queryset = queryset.exclude(estado='leido')

        tipo_notificacion = self.request.query_params.get('tipo_notificacion')
        if tipo_notificacion:
            queryset = queryset.filter(tipo_notificacion__nombre=tipo_notificacion)

        canal = self.request.query_params.get('canal')
        if canal:
            queryset = queryset.filter(canal_notificacion__nombre=canal)

        return queryset

    @action(detail=True, methods=['post'])
    def marcar_leida(self, request, pk=None):
        """
        Marca una notificación como leída
        """
        try:
            usuario = Usuario.objects.get(correoelectronico=request.user.email)
            exito = notification_service.marcar_notificacion_como_leida(int(pk), usuario)

            if exito:
                return Response(
                    {"detail": "Notificación marcada como leída"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": "No se pudo marcar la notificación como leída"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def marcar_todas_leidas(self, request):
        """
        Marca todas las notificaciones no leídas como leídas
        """
        try:
            usuario = Usuario.objects.get(correoelectronico=request.user.email)

            notificaciones_actualizadas = HistorialNotificacion.objects.filter(
                usuario=usuario,
                estado__in=['enviado', 'entregado']
            ).update(
                estado='leido',
                fecha_lectura=notification_service._obtener_timezone_now()
            )

            return Response(
                {
                    "detail": "Notificaciones marcadas como leídas",
                    "cantidad_actualizada": notificaciones_actualizadas
                },
                status=status.HTTP_200_OK
            )

        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )


class PlantillaNotificacionViewSet(ModelViewSet):
    """
    ViewSet para gestionar plantillas de notificación (solo admin)
    """
    queryset = PlantillaNotificacion.objects.all().select_related(
        'tipo_notificacion', 'canal_notificacion'
    )
    serializer_class = PlantillaNotificacionSerializer
    permission_classes = [IsAdminUser]


# =============================================================================
# API Views para Preferencias del Usuario
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_preferencias_usuario(request):
    """
    Obtiene todas las preferencias de notificación del usuario actual
    """
    try:
        usuario = Usuario.objects.get(correoelectronico=request.user.email)
        preferencias = notification_service.obtener_preferencias_usuario(usuario)

        return Response(preferencias, status=status.HTTP_200_OK)

    except Usuario.DoesNotExist:
        return Response(
            {"detail": "Usuario no encontrado en el sistema"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def actualizar_preferencias_usuario(request):
    """
    Actualiza las preferencias de notificación del usuario
    """
    try:
        usuario = Usuario.objects.get(correoelectronico=request.user.email)

        serializer = ActualizarPreferenciasSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                resultado = notification_service.actualizar_preferencias_usuario(
                    usuario, serializer.validated_data
                )

            return Response({
                "detail": "Preferencias actualizadas correctamente",
                "resultado": resultado
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Usuario.DoesNotExist:
        return Response(
            {"detail": "Usuario no encontrado en el sistema"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activar_preferencias_default(request):
    """
    Activa las preferencias por defecto para un usuario nuevo
    """
    try:
        usuario = Usuario.objects.get(correoelectronico=request.user.email)

        # Preferencias por defecto
        preferencias_default = {
            'cita_recordatorio_email': True,
            'cita_recordatorio_push': True,
            'cita_confirmacion_email': True,
            'cita_confirmacion_push': True,
            'cita_cancelacion_email': True,
            'cita_cancelacion_push': True,
            'resultado_disponible_email': True,
            'resultado_disponible_push': False,  # Solo email por defecto
            'factura_generada_email': True,
            'factura_generada_push': False,
            'pago_confirmado_email': True,
            'pago_confirmado_push': False,
        }

        with transaction.atomic():
            resultado = notification_service.actualizar_preferencias_usuario(
                usuario, preferencias_default
            )

        return Response({
            "detail": "Preferencias por defecto activadas correctamente",
            "resultado": resultado
        }, status=status.HTTP_200_OK)

    except Usuario.DoesNotExist:
        return Response(
            {"detail": "Usuario no encontrado en el sistema"},
            status=status.HTTP_404_NOT_FOUND
        )


# =============================================================================
# API Views para Administración
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAdminUser])
def enviar_notificacion_manual(request):
    """
    Permite a los administradores enviar notificaciones manuales
    """
    serializer = EnviarNotificacionSerializer(data=request.data)

    if serializer.is_valid():
        try:
            usuarios = Usuario.objects.filter(
                codigo__in=serializer.validated_data['usuarios']
            )

            if not usuarios.exists():
                return Response(
                    {"detail": "No se encontraron usuarios válidos"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            resultado = notification_service.enviar_notificacion(
                usuarios=list(usuarios),
                tipo_notificacion_nombre=serializer.validated_data['tipo_notificacion'],
                titulo=serializer.validated_data['titulo'],
                mensaje=serializer.validated_data['mensaje'],
                canales=serializer.validated_data['canales'],
                datos_adicionales=serializer.validated_data.get('datos_adicionales'),
                usar_plantilla=False  # Notificaciones manuales no usan plantillas
            )

            return Response({
                "detail": "Notificación enviada",
                "resultado": resultado
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Error enviando notificación: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def inicializar_sistema_notificaciones(request):
    """
    Inicializa los tipos y canales de notificación por defecto
    """
    try:
        notification_service.crear_tipos_notificacion_default()

        return Response({
            "detail": "Sistema de notificaciones inicializado correctamente"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"detail": f"Error inicializando sistema: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def estadisticas_notificaciones(request):
    """
    Obtiene estadísticas del sistema de notificaciones
    """
    try:
        # Estadísticas básicas
        total_usuarios = Usuario.objects.count()
        total_dispositivos = DispositivoMovil.objects.filter(activo=True).count()
        total_notificaciones = HistorialNotificacion.objects.count()

        # Notificaciones por estado
        notificaciones_por_estado = {}
        estados = HistorialNotificacion.objects.values_list('estado', flat=True).distinct()
        for estado in estados:
            notificaciones_por_estado[estado] = HistorialNotificacion.objects.filter(estado=estado).count()

        # Notificaciones por canal
        notificaciones_por_canal = {}
        canales = CanalNotificacion.objects.filter(activo=True)
        for canal in canales:
            count = HistorialNotificacion.objects.filter(canal_notificacion=canal).count()
            notificaciones_por_canal[canal.get_nombre_display()] = count

        # Usuarios con preferencias activas
        usuarios_con_email = PreferenciaNotificacion.objects.filter(
            canal_notificacion__nombre='email', activo=True
        ).values('usuario').distinct().count()

        usuarios_con_push = PreferenciaNotificacion.objects.filter(
            canal_notificacion__nombre='push', activo=True
        ).values('usuario').distinct().count()

        return Response({
            "total_usuarios": total_usuarios,
            "total_dispositivos_activos": total_dispositivos,
            "total_notificaciones_enviadas": total_notificaciones,
            "usuarios_con_email_activo": usuarios_con_email,
            "usuarios_con_push_activo": usuarios_con_push,
            "notificaciones_por_estado": notificaciones_por_estado,
            "notificaciones_por_canal": notificaciones_por_canal,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"detail": f"Error obteniendo estadísticas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )