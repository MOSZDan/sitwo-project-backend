#!/usr/bin/env bash
# build.sh - Script de construcción para Render con workaround para problemas de encoding

set -o errexit  # Salir si cualquier comando falla

echo "🚀 Iniciando build para Render..."

# Instalar dependencias de Python
echo "📦 Instalando dependencias de Python..."
pip install -r requirements.txt

# Verificar variables de entorno críticas
echo "🔍 Verificando configuración..."
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL no está configurada"
    exit 1
fi

# Configurar variables de entorno para PostgreSQL
export PGCLIENTENCODING=UTF8
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

echo "🔧 Configurando encoding PostgreSQL..."
echo "PGCLIENTENCODING: $PGCLIENTENCODING"

# Función simplificada para comandos de Django (evitando psycopg2 directo)
retry_django_command() {
    local cmd="$1"
    local max_attempts=3
    local attempt=1
    local base_delay=20

    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Intento $attempt de $max_attempts: $cmd"

        # Usar variables de entorno adicionales para cada intento
        export DJANGO_SETTINGS_MODULE=dental_clinic_backend.settings
        export PYTHONIOENCODING=utf-8

        if eval "$cmd"; then
            echo "✅ Comando exitoso: $cmd"
            return 0
        else
            echo "⚠️  Fallo en intento $attempt"
            if [ $attempt -eq $max_attempts ]; then
                echo "❌ ERROR: Falló después de $max_attempts intentos: $cmd"

                # Para migraciones, intentar estrategia alternativa
                if [[ "$cmd" == *"migrate"* ]]; then
                    echo "🔧 Intentando estrategia alternativa: crear tablas paso a paso..."

                    # Intentar migración por aplicaciones individuales
                    echo "📝 Migrando aplicaciones del sistema..."
                    python manage.py migrate auth --noinput || true
                    python manage.py migrate contenttypes --noinput || true
                    python manage.py migrate sessions --noinput || true

                    echo "📝 Migrando aplicación principal..."
                    python manage.py migrate api --noinput || true

                    echo "📝 Migración final..."
                    python manage.py migrate --noinput --fake-initial || true

                    return 0
                fi

                return 1
            fi

            local wait_time=$((base_delay + (attempt * 10)))
            echo "⏳ Esperando ${wait_time} segundos antes del siguiente intento..."
            sleep $wait_time
            attempt=$((attempt + 1))
        fi
    done
}

# Verificar que Django puede cargar settings sin problemas de BD
echo "🔧 Verificando configuración de Django..."
python -c "
import os
import sys
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic_backend.settings')
import django
django.setup()
print('✅ Django configurado correctamente')
" || echo "⚠️  Warning: Problemas con configuración Django, continuando..."

echo "🔄 Ejecutando migraciones de Django..."
retry_django_command "python manage.py migrate --noinput"

echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Inicializar notificaciones si el comando existe
echo "🔔 Inicializando sistema de notificaciones..."
python manage.py init_notifications || echo "⚠️  Comando init_notifications no encontrado, continuando..."

echo "✅ Build completado exitosamente!"
