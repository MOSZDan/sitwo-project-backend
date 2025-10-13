from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views, views_auth, views_saas, views_stripe
from .views import UserProfileView, ping
from no_show_policies.views import PoliticaNoShowViewSet  # App externa

router = DefaultRouter()
router.register(r"pacientes", views.PacienteViewSet, basename="pacientes")
router.register(r"consultas", views.ConsultaViewSet, basename="consultas")
router.register(r"odontologos", views.OdontologoViewSet, basename="odontologos")

router.register(r"politicas-no-show", PoliticaNoShowViewSet, basename="politicas-no-show")
router.register(r"estadodeconsultas", views.EstadodeconsultaViewSet, basename="estadodeconsultas")

router.register(r"horarios", views.HorarioViewSet, basename="horarios")
router.register(r"tipos-consulta", views.TipodeconsultaViewSet, basename="tipos-consulta")

# Admin
router.register(r"tipos-usuario", views.TipodeusuarioViewSet, basename="tipos-usuario")
router.register(r"usuarios", views.UsuarioViewSet, basename="usuarios")
router.register(r"bitacora", views.BitacoraViewSet, basename="bitacora")

# Historias Clínicas (HCE)
router.register(r"historias-clinicas", views.HistorialclinicoViewSet, basename="historias-clinicas")

# Consentimiento Digital
router.register(r"consentimientos", views.ConsentimientoViewSet, basename="consentimientos")

urlpatterns = [
    # Health/basic
    path("health/", views.health),
    path("db/", views.db_info),
    path("users/count/", views.users_count),
    path("ping/", ping),

    # Público (SaaS)
    path("public/registrar-empresa/", views_saas.registrar_empresa, name="registrar-empresa"),
    path("public/validar-subdomain/", views_saas.validar_subdomain, name="validar-subdomain"),
    path("public/info/", views_saas.info_sistema, name="info-sistema"),
    path("public/empresa/<str:subdomain>/", views_saas.verificar_empresa_por_subdomain, name="verificar-empresa"),

    # Stripe (Pagos)
    path("public/create-payment-intent/", views_stripe.create_payment_intent, name="create-payment-intent"),
    path("public/registrar-empresa-pago/", views_stripe.registrar_empresa_con_pago, name="registrar-empresa-pago"),
    path("public/stripe-webhook/", views_stripe.stripe_webhook, name="stripe-webhook"),

    # Auth
    path("auth/csrf/", views_auth.csrf_token),
    path("auth/register/", views_auth.auth_register),
    path("auth/login/", views_auth.auth_login),
    path("auth/logout/", views_auth.auth_logout),

    # Perfil de usuario (única ruta para evitar conflicto)
    path("auth/user/", UserProfileView.as_view(), name="user-profile"),

    # Perfil legacy (si aún lo usan en frontend)
    path("usuario/me", views_auth.UsuarioMeView.as_view(), name="usuario-me"),

    # Reset de contraseña
    path("auth/password-reset/", views_auth.password_reset_request),
    path("auth/password-reset-confirm/", views_auth.password_reset_confirm),

    # Notificaciones y preferencias
    path("notificaciones/", include("api.urls_notifications")),
    path("auth/user/settings/", views_auth.auth_user_settings_update),
    path("auth/user/notifications/", views_auth.notification_preferences),

    # Rutas de los ViewSets
    path("", include(router.urls)),

    # Notificaciones mobile
    path("mobile-notif/", include("api.notifications_mobile.urls")),
]