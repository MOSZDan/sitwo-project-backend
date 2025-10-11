#!/bin/bash

# Script automatizado para corregir el error 502 Bad Gateway

set -e

echo "========================================="
echo "CORRECCIÓN AUTOMATIZADA - ERROR 502"
echo "========================================="
echo ""

echo "Este script va a:"
echo "  1. Eliminar configuraciones duplicadas de Nginx"
echo "  2. Actualizar Nginx para usar puerto 8000 en lugar de socket Unix"
echo "  3. Recargar Nginx"
echo "  4. Verificar que todo funcione"
echo ""
read -p "¿Continuar? (s/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Operación cancelada"
    exit 1
fi

echo ""
echo "=== PASO 1: Eliminar configuraciones duplicadas ==="
echo ""

if [ -f /etc/nginx/sites-enabled/dental_clinic_backend ]; then
    echo "Eliminando configuración duplicada: dental_clinic_backend"
    sudo rm /etc/nginx/sites-enabled/dental_clinic_backend
    echo "✅ Eliminada"
else
    echo "✅ No hay configuración duplicada dental_clinic_backend"
fi

echo ""
echo "=== PASO 2: Actualizar configuración de Nginx ==="
echo ""

# Crear nueva configuración
cat > /tmp/dental_clinic.conf << 'EOF'
# Configuración de Nginx para Django Multi-Tenant
# Actualizada para usar puerto 8000

upstream dental_clinic {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name notificct.dpdns.org *.notificct.dpdns.org;

    client_max_body_size 20M;

    # Logs
    access_log /var/log/nginx/dental_clinic_access.log;
    error_log /var/log/nginx/dental_clinic_error.log;

    # Archivos estáticos
    location /static/ {
        alias /home/ubuntu/sitwo-project-backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Archivos media
    location /media/ {
        alias /home/ubuntu/sitwo-project-backend/media/;
        expires 7d;
    }

    # Health check para load balancer
    location /api/health/ {
        proxy_pass http://dental_clinic;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # No cache para health checks
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        proxy_cache_bypass 1;
        proxy_no_cache 1;
    }

    # Proxy a Django/Gunicorn
    location / {
        proxy_pass http://dental_clinic;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

echo "Reemplazando configuración de Nginx..."
sudo mv /tmp/dental_clinic.conf /etc/nginx/sites-available/dental_clinic
echo "✅ Configuración actualizada"

echo ""
echo "=== PASO 3: Verificar configuración de Nginx ==="
echo ""

if sudo nginx -t; then
    echo "✅ Configuración de Nginx válida"
else
    echo "❌ Error en la configuración de Nginx"
    echo "Revirtiendo cambios..."
    exit 1
fi

echo ""
echo "=== PASO 4: Recargar Nginx ==="
echo ""

sudo systemctl reload nginx
echo "✅ Nginx recargado"

echo ""
echo "=== PASO 5: Verificar que Gunicorn esté en puerto 8000 ==="
echo ""

if sudo ss -tlnp | grep -q ":8000"; then
    echo "✅ Gunicorn está corriendo en puerto 8000"
else
    echo "⚠️  Gunicorn no está en puerto 8000"
    echo "Ejecutando script de inicio de Django..."
    cd ~/sitwo-project-backend
    bash deploy/start_django.sh
fi

echo ""
echo "========================================="
echo "✅ CORRECCIÓN COMPLETADA"
echo "========================================="
echo ""
echo "Ahora ejecuta el script de verificación para confirmar:"
echo "  bash deploy/verify_fix.sh"
echo ""