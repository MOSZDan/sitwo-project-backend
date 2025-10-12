# api/notifications_mobile/auth.py
"""
Auth auxiliar OPCIONAL para endpoints de este submódulo.
No se usa en tu API actual; sirve si alguna vez incluyes estas urls.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings

class MobileNotificationsHeaderAuth(BaseAuthentication):
    """
    Autenticación por cabecera X-Notifications-Key (solo para pruebas).
    No interfiere con auth ya existente.
    """
    def authenticate(self, request):
        expected = getattr(settings, "MOBILE_NOTIF_SECRET", None)
        given = request.headers.get("X-Notifications-Key")
        if not expected:
            return None
        if given != expected:
            raise exceptions.AuthenticationFailed("Invalid notification key")
        # Usuario anónimo (solo valida cabecera)
        return (None, None)
