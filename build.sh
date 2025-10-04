#!/usr/bin/env bash
# build.sh - Script de construcción para Render con manejo especial para Supabase

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

# Función mejorada para reintentar comandos con la base de datos
retry_db_command() {
    local cmd="$1"
    local max_attempts=3
    local attempt=1
    local base_delay=15

    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Intento $attempt de $max_attempts: $cmd"

        # Aumentar timeout progresivamente
        local timeout=$((base_delay * attempt))
        echo "⏱️  Timeout configurado a ${timeout}s para este intento"

        if timeout ${timeout}s bash -c "$cmd"; then
            echo "✅ Comando exitoso: $cmd"
            return 0
        else
            echo "⚠️  Fallo en intento $attempt"
            if [ $attempt -eq $max_attempts ]; then
                echo "❌ ERROR: Falló después de $max_attempts intentos: $cmd"

                # Intentar con comando de migración más simple
                if [[ "$cmd" == *"migrate"* ]]; then
                    echo "🔧 Intentando migración con --fake-initial como último recurso..."
                    if python manage.py migrate --fake-initial --noinput; then
                        echo "✅ Migración exitosa con --fake-initial"
                        return 0
                    fi
                fi

                return 1
            fi

            local wait_time=$((base_delay + (attempt * 5)))
            echo "⏳ Esperando ${wait_time} segundos antes del siguiente intento..."
            sleep $wait_time
            attempt=$((attempt + 1))
        fi
    done
}

# Intentar primero una conexión simple para verificar que la base esté disponible
echo "🔌 Probando conectividad básica de la base de datos..."
retry_db_command "python -c \"
import os
import psycopg2
from urllib.parse import urlparse

url = urlparse(os.getenv('DATABASE_URL'))
conn = psycopg2.connect(
    host=url.hostname,
    port=url.port,
    user=url.username,
    password=url.password,
    database=url.path[1:],
    sslmode='require',
    connect_timeout=30,
    application_name='dental_clinic_test'
)
conn.close()
print('✅ Conexión a base de datos exitosa')
\""

echo "🔄 Ejecutando migraciones de Django..."
retry_db_command "python manage.py migrate --noinput"

echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Inicializar notificaciones si el comando existe
echo "🔔 Inicializando sistema de notificaciones..."
python manage.py init_notifications || echo "⚠️  Comando init_notifications no encontrado, continuando..."

echo "✅ Build completado exitosamente!"
