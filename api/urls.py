# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_auth, views_saas, views_stripe
from .views import UserProfileView
from django.urls import path
from no_show_policies.views import PoliticaNoShowViewSet
from no_show_policies.views import PoliticaNoShowViewSet, EstadodeconsultaViewSet
from .views import ping

router = DefaultRouter()
router.register(r"pacientes", views.PacienteViewSet, basename="pacientes")
router.register(r"consultas", views.ConsultaViewSet, basename="consultas")
router.register(r"odontologos", views.OdontologoViewSet, basename="odontologos")
router.register(r'estadodeconsultas', EstadodeconsultaViewSet, basename='estadodeconsultas')
router.register(r'politicas-no-show', PoliticaNoShowViewSet)
router.register(r"horarios", views.HorarioViewSet, basename="horarios")
router.register(r"tipos-consulta", views.TipodeconsultaViewSet, basename="tipos-consulta")

# 👇 SOLO AÑADIR ESTAS DOS RUTAS (admin)
router.register(r"tipos-usuario", views.TipodeusuarioViewSet, basename="tipos-usuario")
router.register(r"usuarios", views.UsuarioViewSet, basename="usuarios")
router.register(r'bitacora', views.BitacoraViewSet, basename='bitacora')

# 👇 NUEVO: Historias Clínicas (HCE)
router.register(r"historias-clinicas", views.HistorialclinicoViewSet, basename="historias-clinicas")

# 👇 NUEVO: Consentimiento Digital
router.register(r"consentimientos", views.ConsentimientoViewSet, basename="consentimientos")

urlpatterns = [
    path("health/", views.health),
    path("db/", views.db_info),
    path("users/count/", views.users_count),
    path("ping/", ping),

    # ====================================
    # ENDPOINTS PÚBLICOS (SaaS)
    # ====================================
    path("public/registrar-empresa/", views_saas.registrar_empresa, name="registrar-empresa"),
    path("public/validar-subdomain/", views_saas.validar_subdomain, name="validar-subdomain"),
    path("public/info/", views_saas.info_sistema, name="info-sistema"),
    path("public/empresa/<str:subdomain>/", views_saas.verificar_empresa_por_subdomain, name="verificar-empresa"),

    # ====================================
    # ENDPOINTS STRIPE (Pagos)
    # ====================================
    path("public/create-payment-intent/", views_stripe.create_payment_intent, name="create-payment-intent"),
    path("public/registrar-empresa-pago/", views_stripe.registrar_empresa_con_pago, name="registrar-empresa-pago"),
    path("public/stripe-webhook/", views_stripe.stripe_webhook, name="stripe-webhook"),
    path('api/', include('no_show_policies.urls')),
    # Auth
    path("auth/csrf/", views_auth.csrf_token),
    path("auth/register/", views_auth.auth_register),
    path("auth/login/", views_auth.auth_login),
    path("auth/logout/", views_auth.auth_logout),
    path("auth/user/", views_auth.auth_user_info),

    # 🔹 Perfil de usuario (legacy) - Lo dejamos por si otra parte lo usa
    path("usuario/me", views_auth.UsuarioMeView.as_view(), name="usuario-me"),

    # Reset de contraseña
    path("auth/password-reset/", views_auth.password_reset_request),
    path("auth/password-reset-confirm/", views_auth.password_reset_confirm),

    # Notificaciones y Preferencias
    path("notificaciones/", include("api.urls_notifications")),
    path("auth/user/settings/", views_auth.auth_user_settings_update),
    path("auth/user/notifications/", views_auth.notification_preferences),
    path('api/', include('no_show_policies.urls')),
    # --- CORRECCIÓN DEFINITIVA ---
    # Eliminamos la ruta conflictiva y dejamos solo esta para el perfil.
    # Ahora manejará GET (leer) y PATCH (actualizar) correctamente.
    path('auth/user/', UserProfileView.as_view(), name='user-profile'),

    # Rutas de los viewsets (router incluido solo una vez)
    path("", include(router.urls)),
    path("mobile-notif/", include("api.notifications_mobile.urls")),
]
