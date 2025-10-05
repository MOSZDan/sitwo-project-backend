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


def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    if not raw:
        return default
    return [x.strip() for x in raw.split(",") if x.strip()]


# Configuración de CORS y hosts dependiendo del entorno
if DEBUG:
    # En desarrollo local - configuración permisiva
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    ALLOWED_HOSTS = ["*"]
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

    # Headers adicionales para desarrollo
    CORS_ALLOW_HEADERS = [
        'accept',
        'accept-encoding',
        'authorization',
        'content-type',
        'dnt',
        'origin',
        'user-agent',
        'x-csrftoken',
        'x-requested-with',
    ]
    CORS_ALLOW_METHODS = [
        'DELETE',
        'GET',
        'OPTIONS',
        'PATCH',
        'POST',
        'PUT',
    ]
else:
    # En producción - configuración estricta
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = _csv_env(
        "CORS_ALLOWED_ORIGINS",
        ["https://sitwo-project.onrender.com"]
    )
    CORS_ALLOW_CREDENTIALS = True
    ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS",
                             ["127.0.0.1", "localhost", "sitwo-project-backend-vzq2.onrender.com"])
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "None")
    CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "None")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Orígenes confiables para CSRF
CSRF_TRUSTED_ORIGINS = _csv_env(
    "CSRF_TRUSTED_ORIGINS",
    [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://sitwo-project.onrender.com",
        "https://sitwo-project-backend-vzq2.onrender.com",
    ] if not DEBUG else [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
)

CSRF_COOKIE_NAME = "csrftoken"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 0 if DEBUG else 60 * 60 * 24 * 30  # 30 días
SECURE_SSL_REDIRECT = not DEBUG

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
    #"rest_framework.authtoken",
    # "rest_framework_simplejwt",
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
    "api.middleware.AuditMiddleware",  # TEMPORALMENTE COMENTADO hasta resolver conexión BD
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
DATABASE_URL = os.getenv("DATABASE_URL")

# NUEVO ENFOQUE: Usar variables individuales como en el script que funciona
# Leer variables de la misma forma que el script local exitoso
DB_USER = os.getenv("user", "postgres.chcnkzxikvjyxvhrsezt")
DB_PASSWORD = os.getenv("password", "yOsOYsUPABASE!")
DB_HOST = os.getenv("host", "aws-1-us-east-2.pooler.supabase.com")
DB_PORT = os.getenv("port", "5432")
DB_NAME = os.getenv("dbname", "postgres")

print(f"🔍 Variables de BD detectadas:")
print(f"  - Usuario: {DB_USER}")
print(f"  - Host: {DB_HOST}")
print(f"  - Puerto: {DB_PORT}")
print(f"  - Base: {DB_NAME}")
print(f"  - DATABASE_URL existe: {'Sí' if DATABASE_URL else 'No'}")

# Probar conexión directa como en el script que funciona
def test_direct_connection():
    """Test de conexión directa usando psycopg2 como en el script local"""
    try:
        import psycopg2
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME
        )
        cursor = connection.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        print(f"✅ Conexión directa exitosa! Timestamp: {result[0]}")
        return True
    except Exception as e:
        print(f"❌ Error en conexión directa: {e}")
        return False

# Ejecutar test de conexión
direct_connection_works = test_direct_connection()

# Configurar DATABASES usando el método que funciona
if direct_connection_works:
    # Si la conexión directa funciona, configurar Django para usar estos parámetros
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'CONN_MAX_AGE': 0,  # Cerrar conexiones inmediatamente
            'CONN_HEALTH_CHECKS': False,
            'OPTIONS': {
                'sslmode': 'require',
                'connect_timeout': 15,
                'keepalives': 0,
                'application_name': 'dental_clinic_render',
            },
        }
    }
    print("✅ Configurando Django con conexión directa que funciona")

elif DATABASE_URL and "postgres" in DATABASE_URL:
    # Fallback: usar DATABASE_URL si existe
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=0,
            conn_health_checks=False,
        )
    }
    DATABASES['default'].update({
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'AUTOCOMMIT': True,
        'ATOMIC_REQUESTS': False,
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 15,
            'keepalives': 0,
            'application_name': 'dental_clinic_render',
        },
    })
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'
    print("⚠️ Usando DATABASE_URL como fallback")

else:
    # Último fallback: SQLite
    print("⚠️ Usando SQLite como último fallback")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
STATIC_ROOT = BASE_DIR / "staticfiles"
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
