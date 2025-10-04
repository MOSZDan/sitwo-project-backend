#!/usr/bin/env bash
# build.sh - Script de construcción para Render con manejo robusto de DB

set -o errexit  # Salir si cualquier comando falla

echo "🚀 Iniciando build para Render..."

# Instalar dependencias de Python
echo "📦 Instalando dependencias de Python..."
pip install -r requirements.txt

# Verificar variables de entorno críticas
echo "🔍 Verificando configuración de base de datos..."
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL no está configurada"
    exit 1
fi

# Función para reintentar comandos con la base de datos
retry_db_command() {
    local cmd="$1"
    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Intento $attempt de $max_attempts: $cmd"

        if eval "$cmd"; then
            echo "✅ Comando exitoso: $cmd"
            return 0
        else
            echo "⚠️  Fallo en intento $attempt"
            if [ $attempt -eq $max_attempts ]; then
                echo "❌ ERROR: Falló después de $max_attempts intentos: $cmd"
                return 1
            fi
            echo "⏳ Esperando 10 segundos antes del siguiente intento..."
            sleep 10
            attempt=$((attempt + 1))
        fi
    done
}

# Validar conexión a la base de datos antes de migrar
echo "🔌 Validando conexión a la base de datos..."
retry_db_command "python manage.py check --database default"

echo "🔄 Ejecutando migraciones de Django..."
retry_db_command "python manage.py migrate --noinput"

echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Inicializar notificaciones si el comando existe
echo "🔔 Inicializando sistema de notificaciones..."
python manage.py init_notifications || echo "⚠️  Comando init_notifications no encontrado, continuando..."

echo "✅ Build completado exitosamente!"
