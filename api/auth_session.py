# api/auth_session.py
"""
Autenticación por sesión de Django (recomendada).
- Usa el AuthenticationMiddleware estándar → request.user es un User real de Django.
- Aplica verificación CSRF automáticamente en POST/PUT/PATCH/DELETE.
- No mantiene estados paralelos en request.session["auth"].
"""

from rest_framework.authentication import SessionAuthentication

class SessionAuth(SessionAuthentication):
    """
    Autenticación por sesión de Django con verificación CSRF en métodos inseguros.
    """
    pass
