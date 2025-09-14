# api/urls_notifications.py - URLs específicas para notificaciones

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views_notifications

# Router para ViewSets
router = DefaultRouter()
router.register(r'tipos-notificacion', views_notifications.TipoNotificacionViewSet, basename='tipos-notificacion')
router.register(r'canales-notificacion', views_notifications.CanalNotificacionViewSet, basename='canales-notificacion')
router.register(r'preferencias', views_notifications.PreferenciaNotificacionViewSet, basename='preferencias')
router.register(r'dispositivos-moviles', views_notifications.DispositivoMovilViewSet, basename='dispositivos-moviles')
router.register(r'historial', views_notifications.HistorialNotificacionViewSet, basename='historial')
router.register(r'plantillas', views_notifications.PlantillaNotificacionViewSet, basename='plantillas')

# URLs adicionales para funciones específicas
urlpatterns = [
    # Incluir las rutas del router
    path('', include(router.urls)),

    # APIs de preferencias del usuario
    path('mis-preferencias/', views_notifications.obtener_preferencias_usuario, name='mis-preferencias'),
    path('actualizar-preferencias/', views_notifications.actualizar_preferencias_usuario,
         name='actualizar-preferencias'),
    path('activar-preferencias-default/', views_notifications.activar_preferencias_default,
         name='activar-preferencias-default'),

    # APIs de administración (solo admin)
    path('admin/enviar-manual/', views_notifications.enviar_notificacion_manual, name='enviar-manual'),
    path('admin/inicializar/', views_notifications.inicializar_sistema_notificaciones, name='inicializar-sistema'),
    path('admin/estadisticas/', views_notifications.estadisticas_notificaciones, name='estadisticas'),
]