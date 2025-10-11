#!/bin/bash

# Script para verificar el estado de los servicios

echo "========================================="
echo "Verificando servicios..."
echo "========================================="
echo ""

echo "1. Estado de Nginx:"
sudo systemctl status nginx --no-pager | grep -A 3 "Active:"
echo ""

echo "2. Estado de Gunicorn:"
sudo systemctl status gunicorn --no-pager | grep -A 3 "Active:" || echo "❌ Gunicorn no está instalado o no está corriendo"
echo ""

echo "3. Verificando si Django responde en puerto 8000:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:8000/api/health/ || echo "❌ Django no responde en puerto 8000"
echo ""

echo "4. Verificando si Nginx responde en puerto 80:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:80/api/health/ || echo "❌ Nginx no responde en puerto 80"
echo ""

echo "5. Últimas 20 líneas del log de error de Nginx:"
sudo tail -20 /var/log/nginx/dental_clinic_error.log 2>/dev/null || echo "No se pudo leer el log de Nginx"
echo ""

echo "6. Procesos de Python en ejecución:"
ps aux | grep python | grep -v grep
echo ""

echo "7. Configuración de Nginx activa:"
ls -la /etc/nginx/sites-enabled/
echo ""

echo "========================================="
echo "Pruebas de conectividad:"
echo "========================================="
echo ""

echo "Probando acceso directo por IP:"
curl -I http://127.0.0.1/ 2>&1 | head -5
echo ""

echo "Probando con header Host: notificct.dpdns.org:"
curl -I -H "Host: notificct.dpdns.org" http://127.0.0.1/ 2>&1 | head -5