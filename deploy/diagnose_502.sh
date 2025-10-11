#!/bin/bash

# Script de diagnóstico completo para error 502 Bad Gateway

echo "========================================="
echo "DIAGNÓSTICO COMPLETO - ERROR 502"
echo "========================================="
echo ""

echo "=== 1. VERIFICANDO SERVICIOS ==="
echo ""

echo "Estado de Nginx:"
sudo systemctl status nginx --no-pager | head -10
echo ""

echo "Estado de Gunicorn:"
sudo systemctl status gunicorn --no-pager | head -10 2>&1
GUNICORN_STATUS=$?
echo ""

echo "=== 2. VERIFICANDO PROCESOS DE PYTHON ==="
echo ""
echo "Procesos de Python corriendo:"
ps aux | grep -E "python|gunicorn|django" | grep -v grep
echo ""

echo "=== 3. VERIFICANDO PUERTOS EN ESCUCHA ==="
echo ""
echo "Procesos escuchando en puertos 80 y 8000:"
sudo netstat -tlnp | grep -E ":80 |:8000 " || sudo ss -tlnp | grep -E ":80 |:8000 "
echo ""

echo "=== 4. PROBANDO CONEXIÓN A DJANGO ==="
echo ""
echo "Intentando conectar a Django en puerto 8000:"
if curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:8000/api/health/ 2>&1; then
    echo " ✅ Django responde"
    curl -s http://127.0.0.1:8000/api/health/ | head -20
else
    echo " ❌ Django NO responde en puerto 8000"
    echo ""
    echo "PROBLEMA ENCONTRADO: Django no está corriendo en el puerto 8000"
fi
echo ""

echo "=== 5. VERIFICANDO CONFIGURACIÓN DE NGINX ==="
echo ""
echo "Archivos de configuración activos:"
ls -la /etc/nginx/sites-enabled/
echo ""

echo "Contenido de la configuración activa:"
cat /etc/nginx/sites-enabled/* 2>/dev/null | head -50
echo ""

echo "=== 6. LOGS DE NGINX (ÚLTIMAS 30 LÍNEAS) ==="
echo ""
echo "Error log:"
sudo tail -30 /var/log/nginx/error.log 2>/dev/null || echo "No se pudo leer error.log"
echo ""

echo "Access log (últimas 10 líneas):"
sudo tail -10 /var/log/nginx/access.log 2>/dev/null || echo "No se pudo leer access.log"
echo ""

echo "=== 7. PROBANDO NGINX ==="
echo ""
echo "Test de configuración de Nginx:"
sudo nginx -t
echo ""

echo "=== 8. VERIFICANDO DIRECTORIO DEL PROYECTO ==="
echo ""
echo "Ubicación del proyecto:"
pwd
ls -la ~/sitwo-project-backend/ 2>/dev/null | head -20 || echo "Directorio no encontrado"
echo ""

echo "=== 9. VARIABLES DE ENTORNO ==="
echo ""
if [ -f ~/sitwo-project-backend/.env ]; then
    echo "Archivo .env existe ✅"
    echo "Contenido (ocultando valores sensibles):"
    cat ~/sitwo-project-backend/.env | grep -E "^[A-Z]" | sed 's/=.*/=***/' | head -20
else
    echo "❌ Archivo .env NO existe"
fi
echo ""

echo "=== 10. RECOMENDACIONES ==="
echo ""

if [ $GUNICORN_STATUS -ne 0 ]; then
    echo "⚠️  PROBLEMA: Gunicorn no está corriendo"
    echo ""
    echo "SOLUCIÓN: Necesitas iniciar tu aplicación Django. Opciones:"
    echo ""
    echo "Opción 1 - Iniciar con Gunicorn manualmente:"
    echo "  cd ~/sitwo-project-backend"
    echo "  source venv/bin/activate  # o el nombre de tu virtualenv"
    echo "  gunicorn dental_clinic_backend.wsgi:application --bind 0.0.0.0:8000 --daemon"
    echo ""
    echo "Opción 2 - Usar systemd service:"
    echo "  sudo systemctl start gunicorn"
    echo ""
    echo "Opción 3 - Usar screen/tmux para desarrollo:"
    echo "  cd ~/sitwo-project-backend"
    echo "  screen -S django"
    echo "  source venv/bin/activate"
    echo "  python manage.py runserver 0.0.0.0:8000"
    echo "  # Presiona Ctrl+A, luego D para salir de screen"
fi

echo ""
echo "========================================="
echo "FIN DEL DIAGNÓSTICO"
echo "========================================="