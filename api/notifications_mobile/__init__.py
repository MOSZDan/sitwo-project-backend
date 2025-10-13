# api/notifications_mobile/__init__.py
"""
Utilidades de notificaciones móviles (aisladas, sin colisión con la API existente).

Para envío FCM vía HTTP v1 usa:
    from api.notifications_mobile.utils import mobile_send_push_fcm

Para encolar en BD:
    from api.notifications_mobile.queue import enqueue_notif, enqueue_notif_for_user_devices
"""
__all__ = [
    "auth",
    "config",
    "serializers",
    "urls",
    "utils",
    "views",
    "models",
    "queue",
    "taxonomy",  # <-- elimina esta línea si no tienes taxonomy.py
]
__version__ = "0.2.0"
