"""
Django settings for dental_clinic_backend project.
"""

from pathlib import Path
import os

# ------------------------------------
# Paths
# ------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------
# Seguridad / Debug
# ------------------------------------
# IMPORTANTE: Usa variables de entorno en producción
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', "django-insecure-cambiar-en-produccion-tu-secret-key-aqui")
DEBUG = os.environ.get('DEBUG', 'False') == 'True'  # Por defecto False en producción
# ------------------------------------
# Seguridad - Allowed Hosts / CORS / CSRF
# ------------------------------------
ALLOWED_HOSTS = [
    "localhost",
    ".dpdns.org",
    "127.0.0.1",
    "3.137.195.59",
    "18.220.214.178",
    ".amazonaws.com",
    "ec2-18-220-214-178.us-east-2.compute.amazonaws.com",
    "sitwo-project.onrender.com",
    "notificct.dpdns.org",
    "balancearin-1841542738.us-east-2.elb.amazonaws.com",
    ".localhost",
    ".notificct.dpdns.org",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.dpdns\.org$",  # Permite https://cualquier-subdominio.dpdns.org
    r"^https://[\w-]+\.notificct\.dpdns\.org$",  # Subdominios de tenants
]

# En desarrollo, permitir todos los orígenes (incluyendo subdominios)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    # En producción, lista específica de orígenes permitidos
    CORS_ALLOWED_ORIGINS = [
        "https://sitwo-project.onrender.com",
        "https://notificct.dpdns.org",  # Dominio público (landing page)
        # Los subdominios de tenants se manejan por el regex de arriba
        "https://norte.notificct.dpdns.org",
        "https://sur.notificct.dpdns.org",
        "https://este.notificct.dpdns.org",
    ]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://sitwo-project.onrender.com",
    "http://18.220.214.178",
    "https://18.220.214.178",
    "https://ec2-18-220-214-178.us-east-2.compute.amazonaws.com",
    # Multi-tenancy: Permitir subdominios en desarrollo
    "http://localhost:5173",
    "http://*.localhost:5173",
    "http://norte.localhost:5173",
    "http://sur.localhost:5173",
    "http://este.localhost:5173",
    # Multi-tenancy: Permitir subdominios en producción
    "https://notificct.dpdns.org",
    "https://*.notificct.dpdns.org",
    "https://*.dpdns.org"
]

# ------------------------------------
# Apps
# ------------------------------------
INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    'django_filters',
    "rest_framework.authtoken",
    "api",
    "whitenoise.runserver_nostatic",
]

# ------------------------------------
# Middleware
# ------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "api.middleware.TenantMiddleware",  # Multi-tenancy: identificar empresa
    "api.middleware.AuditMiddleware",  # Auditoría (después de TenantMiddleware)
]

ROOT_URLCONF = "dental_clinic_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "dental_clinic_backend.wsgi.application"

# ------------------------------------
# Base de datos (Configuración simplificada para Render + Supabase)
# ------------------------------------

AWS_ACCESS_KEY_ID = 'AKIAYF2ZN5QS4TV4QHE5'
AWS_SECRET_ACCESS_KEY = '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'
AWS_STORAGE_BUCKET_NAME = 'dentalclinicbackend'
AWS_S3_SIGNATURE_NAME = 's3v4',
AWS_S3_REGION_NAME = 'us-east-2'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_VERITY = True
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "clinicaldentt",
        "USER": "postgres",
        "PASSWORD": "pedritopicapiedra",
        "HOST": "clinicadentalapp.ctwuseyooir4.us-east-2.rds.amazonaws.com",
        "PORT": "5432",
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}

# ------------------------------------
# Password validators
# ------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------
# Localización
# ------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

# ------------------------------------
# Archivos estáticos (WhiteNoise)
# ------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URLS = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ------------------------------------
# DRF - CORREGIDO
# ------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    'DEFAULT_THROTTLE_RATES': {
        'notifications': '100/hour',
        'device_registration': '10/day',
        'preference_updates': '50/hour',
    }
}

# ------------------------------------
# Otros
# ------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------
# Frontend y Email (para recuperar contraseña)
# ------------------------------------
FRONTEND_URL = "https://sitwo-project.onrender.com"
DEFAULT_FROM_EMAIL = "no-reply@clinica.local"

# ------------------------------------
# SaaS Multi-Tenant Configuration
# ------------------------------------
# Dominio base para tenants (sin https://)
SAAS_BASE_DOMAIN = "notificct.dpdns.org"

# URL del sitio público (landing page de ventas)
# Este es el dominio SIN subdominio donde los clientes se registran
SAAS_PUBLIC_URL = f"https://{SAAS_BASE_DOMAIN}"

# Ejemplo de URLs resultantes:
# - Sitio público: https://notificct.dpdns.org
# - Tenant "norte": https://norte.notificct.dpdns.org
# - Tenant "sur": https://sur.notificct.dpdns.org

# ------------------------------------
# Configuración de Email (SMTP)
# ------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.resend.com"  # Cambia esto por tu proveedor de email
EMAIL_PORT = 587
EMAIL_HOST_USER = "apikey"  # Usuario de tu servicio de email
EMAIL_HOST_PASSWORD = ""  # IMPORTANTE: Agrega aquí tu API key de email
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

# ------------------------------------
# CONFIGURACIÓN DE NOTIFICACIONES
# ------------------------------------

# Push Notifications (OneSignal - Opcional)
ONESIGNAL_APP_ID = ""  # Agrega tu OneSignal App ID aquí
ONESIGNAL_REST_API_KEY = ""  # Agrega tu OneSignal REST API Key aquí

# ------------------------------------
# Stripe (Pagos SaaS - Opcional)
# ------------------------------------
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', "pk_test_51SGSX5RxIhITCnEhwyPtoKa0LAWxHpMcr3Tw20Aqw9vkB8ncErHhIP1IvXmQjTdovbeQQMx55dGqiKqvTrJsjevj00Qd4GEebn")
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', "")  # IMPORTANTE: Agrega tu Stripe Secret Key como variable de entorno
STRIPE_PRICE_ID = os.environ.get('STRIPE_PRICE_ID', "price_1SGVmoRxIhITCnEhEPfNBLzt")
STRIPE_PRICE_AMOUNT = 99  # Precio en USD del plan mensual (solo para mostrar al usuario)
STRIPE_CURRENCY = "usd"  # Moneda
STRIPE_WEBHOOK_SECRET = ""  # Agrega tu webhook secret de Stripe

# Configuración de notificaciones por email
DEFAULT_REMINDER_HOURS = 24
MAX_NOTIFICATION_RETRIES = 3
NOTIFICATION_RETRY_DELAY = 30

# Información de la clínica para emails
CLINIC_INFO = {
    'name': "Clínica Dental",
    'address': "Santa Cruz, Bolivia",
    'phone': "+591 XXXXXXXX",
    'email': "info@clinica.com",
    'website': FRONTEND_URL,
}

# Configuración de logging para notificaciones
import os

logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Throttling para APIs de notificaciones
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_RATES': {
        'notifications': '100/hour',
        'device_registration': '10/day',
        'preference_updates': '50/hour',
    }
})
# Al final de settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ------------------------------------
# Configuraciones de Seguridad para Producción
# ------------------------------------
if not DEBUG:
    # HTTPS/SSL Settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Security Headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
