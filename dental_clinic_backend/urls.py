"""
URL configuration for dental_clinic_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
1. Import the include() function: from django.urls import include, path
2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from PIL.SpiderImagePlugin import iforms
# dental_clinic_backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls.static import static

def api_welcome(request):
    """Vista de bienvenida para la API"""
    return JsonResponse({
        "message": "🦷 Clínica Dental API - Backend funcionando correctamente",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "admin": "/admin/",
            "api": "/api/",
            "documentation": "/api/docs/" if hasattr(request, 'user') else "Coming soon"
        }
    })

urlpatterns = [
    path("", api_welcome, name="welcome"),  # Vista de bienvenida para la raíz
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_URL)
