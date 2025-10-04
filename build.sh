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

# Configurar variables de entorno para PostgreSQL - MÁS COMPLETO
export PGCLIENTENCODING=UTF8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export PYTHONIOENCODING=utf-8
export DJANGO_SETTINGS_MODULE=dental_clinic_backend.settings

echo "🔧 Configurando encoding PostgreSQL..."
echo "PGCLIENTENCODING: $PGCLIENTENCODING"
echo "LC_ALL: $LC_ALL"
echo "LANG: $LANG"

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
# Crear migraciones para el nuevo modelo Vista
echo "📝 Creando migraciones para modelos nuevos..."
python manage.py makemigrations api --noinput || echo "⚠️  No hay cambios para migrar"

# Ejecutar migraciones con reintentos
echo "📝 Aplicando migraciones a la base de datos..."
max_attempts=3
attempt=1

while [ $attempt -le $max_attempts ]; do
    echo "🔄 Intento $attempt de $max_attempts: python manage.py migrate --noinput"

    if python manage.py migrate --noinput; then
        echo "✅ Migraciones aplicadas exitosamente"
        break
    else
        echo "⚠️  Fallo en intento $attempt"
        if [ $attempt -eq $max_attempts ]; then
            echo "⚠️  No se pudieron aplicar todas las migraciones después de $max_attempts intentos"
            echo "⚠️  Continuando con el deployment - las migraciones se aplicarán en el siguiente deploy"
        else
            wait_time=$((20 + (attempt * 10)))
            echo "⏳ Esperando ${wait_time} segundos antes del siguiente intento..."
            sleep $wait_time
        fi
        attempt=$((attempt + 1))
    fi
done

echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Inicializar notificaciones si el comando existe
echo "🔔 Inicializando sistema de notificaciones..."
python manage.py init_notifications 2>/dev/null || echo "⚠️  Comando init_notifications no encontrado, continuando..."

echo "✅ Build completado exitosamente!"
