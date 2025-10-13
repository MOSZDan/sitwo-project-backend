#!/bin/bash

# Script para corregir la configuración de Nginx y solucionar el error 502 Bad Gateway
# Este script debe ejecutarse en la instancia EC2

set -e

echo "========================================="
echo "Corrigiendo configuración de Nginx..."
echo "========================================="

# Crear configuración de Nginx corregida
cat > /tmp/dental_clinic_backend.conf << 'EOF'
# Configuración de Nginx para Dental Clinic Backend
# Soporte para dominio principal y subdominios multi-tenant

upstream django_app {
    server 127.0.0.1:8000;
}

# Server block para el dominio principal y todos los subdominios
server {
    listen 80;
    server_name notificct.dpdns.org *.notificct.dpdns.org;

    client_max_body_size 100M;

    # Logs
    access_log /var/log/nginx/dental_clinic_access.log;
    error_log /var/log/nginx/dental_clinic_error.log;

    # Health check endpoint (para ALB)
    location /api/health/ {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static/ {
        alias /home/ubuntu/sitwo-project-backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/ubuntu/sitwo-project-backend/media/;
        expires 30d;
    }

    # Todas las demás peticiones a Django
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

echo "Moviendo nueva configuración a /etc/nginx/sites-available/..."
sudo mv /tmp/dental_clinic_backend.conf /etc/nginx/sites-available/dental_clinic_backend

echo "Habilitando sitio..."
sudo ln -sf /etc/nginx/sites-available/dental_clinic_backend /etc/nginx/sites-enabled/

echo "Eliminando configuración default si existe..."
sudo rm -f /etc/nginx/sites-enabled/default

echo "Verificando configuración de Nginx..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "Configuración válida. Reiniciando Nginx..."
    sudo systemctl reload nginx
    echo ""
    echo "========================================="
    echo "✅ Nginx configurado correctamente"
    echo "========================================="
    echo ""
    echo "Estado del servicio Nginx:"
    sudo systemctl status nginx --no-pager
    echo ""
    echo "Estado del servicio Gunicorn:"
    sudo systemctl status gunicorn --no-pager || echo "⚠️  Gunicorn no está corriendo. Inícialo con: sudo systemctl start gunicorn"
else
    echo "❌ Error en la configuración de Nginx"
    exit 1
fi

echo ""
echo "Para ver los logs de Nginx en tiempo real:"
echo "  sudo tail -f /var/log/nginx/dental_clinic_error.log"
echo ""
echo "Para verificar que Gunicorn está corriendo:"
echo "  sudo systemctl status gunicorn"
echo "  curl http://127.0.0.1:8000/api/health/"