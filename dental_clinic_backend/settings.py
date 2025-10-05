"""
Django settings for dental_clinic_backend project.
"""

from pathlib import Path
import os

from dotenv import load_dotenv
import dj_database_url

# ------------------------------------
# Paths / .env
# ------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ------------------------------------
# Seguridad / Debug
# ------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-not-secret")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
# ------------------------------------
# Seguridad - Allowed Hosts / CORS / CSRF
# ------------------------------------
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "3.137.195.59",
    "18.220.214.178",
    ".amazonaws.com",
    "ec2-18-220-214-178.us-east-2.compute.amazonaws.com",
    "sitwo-project.onrender.com",
    "127.0.0.1:5173"
]

CORS_ALLOWED_ORIGINS = [
    "https://sitwo-project.onrender.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173"
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "https://sitwo-project.onrender.com",
    "http://18.220.214.178",
    "https://18.220.214.178",
    "https://ec2-18-220-214-178.us-east-2.compute.amazonaws.com",
    "http://127.0.0.1:5173"
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
    "api.middleware.AuditMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
AWS_DEFAULT_ACL =  None
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
STATIC_ROOT = os.path.join(BASE_DIR,'staticfiles')
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
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://sitwo-project.onrender.com")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@clinica.local")

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.resend.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "apikey")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"


# ------------------------------------
# 🆕 CONFIGURACIÓN DE NOTIFICACIONES
# ------------------------------------

# Push Notifications usando Supabase Edge Functions (alternativa a Firebase)
ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID", "")
ONESIGNAL_REST_API_KEY = os.getenv("ONESIGNAL_REST_API_KEY", "")

# Configuración de notificaciones por email
DEFAULT_REMINDER_HOURS = int(os.getenv("DEFAULT_REMINDER_HOURS", "24"))
MAX_NOTIFICATION_RETRIES = int(os.getenv("MAX_NOTIFICATION_RETRIES", "3"))
NOTIFICATION_RETRY_DELAY = int(os.getenv("NOTIFICATION_RETRY_DELAY", "30"))

# Información de la clínica para emails
CLINIC_INFO = {
    'name': os.getenv("CLINIC_NAME", "Clínica Dental"),
    'address': os.getenv("CLINIC_ADDRESS", "Santa Cruz, Bolivia"),
    'phone': os.getenv("CLINIC_PHONE", "+591 XXXXXXXX"),
    'email': os.getenv("CLINIC_EMAIL", "info@clinica.com"),
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
