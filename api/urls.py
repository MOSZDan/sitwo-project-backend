# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_auth

router = DefaultRouter()
router.register(r"pacientes", views.PacienteViewSet, basename="pacientes")
router.register(r"consultas", views.ConsultaViewSet, basename="consultas")

urlpatterns = [
    path("health/", views.health),
    path("db/", views.db_info),
    path("users/count/", views.users_count),

    # Auth (sesión)
    path("auth/csrf/", views_auth.csrf_token),
    path("auth/register/", views_auth.auth_register),

    path("", include(router.urls)),
]
