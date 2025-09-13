# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_auth

router = DefaultRouter()
router.register(r"pacientes", views.PacienteViewSet, basename="pacientes")
router.register(r"consultas", views.ConsultaViewSet, basename="consultas")
router = DefaultRouter()
router.register(r"pacientes", views.PacienteViewSet, basename="pacientes")
router.register(r"consultas", views.ConsultaViewSet, basename="consultas")
# 👇 AÑADE ESTAS NUEVAS RUTAS
router.register(r"odontologos", views.OdontologoViewSet, basename="odontologos")
router.register(r"horarios", views.HorarioViewSet, basename="horarios")
router.register(r"tipos-consulta", views.TipodeconsultaViewSet, basename="tipos-consulta")

# 👇 SOLO AÑADIR ESTAS DOS RUTAS (admin)
router.register(r"tipos-usuario", views.TipodeusuarioViewSet, basename="tipos-usuario")
router.register(r"usuarios", views.UsuarioViewSet, basename="usuarios")

urlpatterns = [
    path("health/", views.health),
    path("db/", views.db_info),
    path("users/count/", views.users_count),

    # Auth
    path("auth/csrf/", views_auth.csrf_token),
    path("auth/register/", views_auth.auth_register),
    path("auth/login/", views_auth.auth_login),
    path("auth/logout/", views_auth.auth_logout),
    path("auth/user/", views_auth.auth_user_info),

    # Recuperación de contraseña
    path("auth/password-reset/", views_auth.password_reset_request),
    path("auth/password-reset-confirm/", views_auth.password_reset_confirm),

    path("", include(router.urls)),

]