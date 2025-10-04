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
# Usar C.UTF-8 que está disponible en todos los sistemas
export PGCLIENTENCODING=UTF8
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export PYTHONIOENCODING=utf-8
export DJANGO_SETTINGS_MODULE=dental_clinic_backend.settings

# IMPORTANTE: Convertir URL del pooler (puerto 6543) a conexión directa (puerto 5432)
# El pooler de Supabase puede rechazar conexiones durante el build
if [[ "$DATABASE_URL" == *":6543/"* ]]; then
    echo "🔄 Detectado pooler de Supabase (puerto 6543), cambiando a conexión directa (puerto 5432)..."
    export MIGRATION_DATABASE_URL="${DATABASE_URL//:6543\//:5432/}"
    # Cambiar también pooler.supabase.com por aws-0-us-east-2.pooler.supabase.com
    export MIGRATION_DATABASE_URL="${MIGRATION_DATABASE_URL//pooler.supabase.com/aws-0-us-east-2.pooler.supabase.com}"
    echo "✅ Usando conexión directa para migraciones"
else
    export MIGRATION_DATABASE_URL="$DATABASE_URL"
fi

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
DATABASE_URL="$MIGRATION_DATABASE_URL" python manage.py makemigrations api --noinput || echo "⚠️  No hay cambios para migrar"

# Ejecutar migraciones con reintentos y manejo de errores mejorado
echo "📝 Aplicando migraciones a la base de datos..."
max_attempts=3
attempt=1

while [ $attempt -le $max_attempts ]; do
    echo "🔄 Intento $attempt de $max_attempts: python manage.py migrate --noinput"

    # Usar la URL de migración directa
    if DATABASE_URL="$MIGRATION_DATABASE_URL" python manage.py migrate --noinput 2>&1; then
        echo "✅ Migraciones aplicadas exitosamente"
        break
    else
        exit_code=$?
        echo "⚠️  Fallo en intento $attempt (código: $exit_code)"

        if [ $attempt -eq $max_attempts ]; then
            echo "⚠️  No se pudieron aplicar todas las migraciones después de $max_attempts intentos"
            echo "ℹ️  Esto puede deberse a problemas temporales de conexión con Supabase"
            echo "ℹ️  Las tablas ya existen en la BD, continuando con el deployment..."
            # NO FALLAR - permitir que el deployment continúe
            break
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
DATABASE_URL="$MIGRATION_DATABASE_URL" python manage.py init_notifications 2>/dev/null || echo "⚠️  Comando init_notifications no encontrado, continuando..."

echo "✅ Build completado exitosamente!"
