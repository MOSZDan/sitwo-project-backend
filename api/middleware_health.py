# api/middleware_health.py
"""
Middleware para permitir conexiones HTTP solo en el endpoint /api/health/
Este es necesario para que los health checks de AWS Load Balancer funcionen correctamente.
"""

class HealthCheckMiddleware:
    """
    Middleware que permite que el endpoint /api/health/ funcione via HTTP
    incluso cuando SECURE_SSL_REDIRECT=True en producción.

    Esto es necesario para los health checks del load balancer que hacen
    peticiones HTTP en lugar de HTTPS.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si es el endpoint de health check, marcar que no requiere SSL redirect
        if request.path in ['/api/health/', '/api/health']:
            request._dont_enforce_csrf_checks = True
            # Desactivar SSL redirect solo para este endpoint
            request._secure_ssl_redirect_exempt = True

        response = self.get_response(request)
        return response