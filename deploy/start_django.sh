#!/bin/bash

# Script para iniciar Django con Gunicorn

set -e

echo "========================================="
echo "Iniciando aplicación Django"
echo "========================================="
echo ""

# Ir al directorio del proyecto
cd ~/sitwo-project-backend

echo "1. Verificando entorno virtual..."
if [ -d "venv" ]; then
    echo "✅ Encontrado: venv"
    source venv/bin/activate
elif [ -d "env" ]; then
    echo "✅ Encontrado: env"
    source env/bin/activate
elif [ -d ".venv" ]; then
    echo "✅ Encontrado: .venv"
    source .venv/bin/activate
else
    echo "⚠️  No se encontró entorno virtual. Creando uno nuevo..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Instalando dependencias..."
    pip install -r requirements.txt
fi

echo ""
echo "2. Verificando instalación de Gunicorn..."
if ! command -v gunicorn &> /dev/null; then
    echo "Instalando Gunicorn..."
    pip install gunicorn
fi

echo ""
echo "3. Verificando archivo .env..."
if [ ! -f .env ]; then
    echo "❌ ERROR: Archivo .env no existe"
    echo "Crea el archivo .env con las variables necesarias"
    exit 1
fi

echo ""
echo "4. Ejecutando migraciones..."
python manage.py migrate --noinput || echo "⚠️  Advertencia: No se pudieron ejecutar migraciones"

echo ""
echo "5. Recolectando archivos estáticos..."
python manage.py collectstatic --noinput || echo "⚠️  Advertencia: No se pudieron recolectar archivos estáticos"

echo ""
echo "6. Matando procesos anteriores de Gunicorn..."
pkill -f gunicorn || echo "No hay procesos de Gunicorn corriendo"
sleep 2

echo ""
echo "7. Iniciando Gunicorn..."
gunicorn dental_clinic_backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --access-logfile /tmp/gunicorn-access.log \
    --error-logfile /tmp/gunicorn-error.log \
    --log-level info \
    --daemon

echo ""
echo "8. Esperando a que Gunicorn inicie..."
sleep 3

echo ""
echo "9. Verificando que Gunicorn esté corriendo..."
if ps aux | grep -v grep | grep gunicorn > /dev/null; then
    echo "✅ Gunicorn está corriendo"
    ps aux | grep gunicorn | grep -v grep
else
    echo "❌ ERROR: Gunicorn no pudo iniciar"
    echo "Revisa los logs:"
    echo "  tail -f /tmp/gunicorn-error.log"
    exit 1
fi

echo ""
echo "10. Probando endpoint de health check..."
sleep 2
curl -I http://127.0.0.1:8000/api/health/ || echo "⚠️  Advertencia: Health check no responde"

echo ""
echo "========================================="
echo "✅ Django iniciado correctamente"
echo "========================================="
echo ""
echo "Logs de Gunicorn:"
echo "  tail -f /tmp/gunicorn-access.log"
echo "  tail -f /tmp/gunicorn-error.log"
echo ""
echo "Para detener Gunicorn:"
echo "  pkill -f gunicorn"