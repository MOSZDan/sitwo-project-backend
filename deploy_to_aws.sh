#!/bin/bash

################################################################################
# SCRIPT DE DESPLIEGUE AUTOMATIZADO A AWS EC2
################################################################################
# Este script automatiza el despliegue completo del backend Django
# en AWS EC2 con Nginx, Gunicorn y configuración SSL
################################################################################

set -e  # Detener el script si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

################################################################################
# CONFIGURACIÓN INICIAL
################################################################################

print_section "INICIO DE DESPLIEGUE AWS EC2"

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    print_error "Este script debe ejecutarse desde el directorio raíz del proyecto Django"
    print_error "Asegúrate de estar en: sitwo-project-backend/"
    exit 1
fi

PROJECT_DIR="/home/ubuntu/sitwo-project-backend"
VENV_DIR="$PROJECT_DIR/venv"
APP_NAME="dental_clinic_backend"

print_message "Directorio del proyecto: $PROJECT_DIR"
print_message "Entorno virtual: $VENV_DIR"

################################################################################
# 1. ACTUALIZAR SISTEMA
################################################################################

print_section "1. ACTUALIZANDO SISTEMA OPERATIVO"
sudo apt-get update -y
sudo apt-get upgrade -y

################################################################################
# 2. INSTALAR DEPENDENCIAS DEL SISTEMA
################################################################################

print_section "2. INSTALANDO DEPENDENCIAS DEL SISTEMA"

print_message "Instalando Python 3.11 y herramientas..."
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    nginx \
    git \
    supervisor \
    postgresql-client \
    libpq-dev \
    build-essential \
    curl \
    certbot \
    python3-certbot-nginx

print_message "✓ Dependencias del sistema instaladas"

################################################################################
# 3. CONFIGURAR DIRECTORIO DEL PROYECTO
################################################################################

print_section "3. CONFIGURANDO DIRECTORIO DEL PROYECTO"

# Crear directorio del proyecto si no existe
if [ ! -d "$PROJECT_DIR" ]; then
    print_message "Creando directorio del proyecto..."
    sudo mkdir -p "$PROJECT_DIR"
    sudo chown ubuntu:ubuntu "$PROJECT_DIR"
fi

# Si el proyecto ya existe, hacer pull de los últimos cambios
if [ -d "$PROJECT_DIR/.git" ]; then
    print_message "Actualizando código desde Git..."
    cd "$PROJECT_DIR"
    git pull origin master || print_warning "No se pudo hacer pull. Continuando..."
else
    print_message "Clonando repositorio..."
    print_warning "NOTA: Debes configurar el repositorio Git manualmente si no existe"
    # git clone <tu-repositorio> "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

################################################################################
# 4. CONFIGURAR ENTORNO VIRTUAL
################################################################################

print_section "4. CONFIGURANDO ENTORNO VIRTUAL DE PYTHON"

# Crear entorno virtual si no existe
if [ ! -d "$VENV_DIR" ]; then
    print_message "Creando entorno virtual..."
    python3.11 -m venv "$VENV_DIR"
fi

# Activar entorno virtual
print_message "Activando entorno virtual..."
source "$VENV_DIR/bin/activate"

# Actualizar pip
print_message "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
print_message "Instalando dependencias de Python..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    print_error "No se encontró requirements.txt"
    exit 1
fi

print_message "✓ Entorno virtual configurado"

################################################################################
# 5. VERIFICAR ARCHIVO .env
################################################################################

print_section "5. VERIFICANDO CONFIGURACIÓN (.env)"

if [ ! -f ".env" ]; then
    print_error "No se encontró el archivo .env"
    print_error "Crea el archivo .env con las siguientes variables:"
    echo ""
    echo "DEBUG=False"
    echo "DJANGO_SECRET_KEY=tu_secret_key_segura"
    echo "DB_NAME=tu_base_de_datos"
    echo "DB_USER=tu_usuario"
    echo "DB_PASSWORD=tu_password"
    echo "DB_HOST=tu_host.supabase.co"
    echo "DB_PORT=5432"
    echo "AWS_ACCESS_KEY_ID=tu_access_key"
    echo "AWS_SECRET_ACCESS_KEY=tu_secret_key"
    echo "AWS_STORAGE_BUCKET_NAME=tu_bucket"
    echo "STRIPE_SECRET_KEY=tu_stripe_secret"
    echo "STRIPE_PUBLIC_KEY=tu_stripe_public"
    echo "STRIPE_PRICE_ID=tu_price_id"
    echo "STRIPE_WEBHOOK_SECRET=tu_webhook_secret"
    echo ""
    exit 1
fi

# Verificar que DEBUG esté en False
if grep -q "DEBUG=True" .env; then
    print_error "DEBUG está en True. Cámbialo a False en producción:"
    print_error "DEBUG=False"
    exit 1
fi

print_message "✓ Archivo .env encontrado y configurado"

################################################################################
# 6. EJECUTAR MIGRACIONES
################################################################################

print_section "6. EJECUTANDO MIGRACIONES DE BASE DE DATOS"

print_message "Aplicando migraciones..."
python manage.py migrate --noinput

print_message "✓ Migraciones aplicadas"

################################################################################
# 7. RECOLECTAR ARCHIVOS ESTÁTICOS
################################################################################

print_section "7. RECOLECTANDO ARCHIVOS ESTÁTICOS"

print_message "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

print_message "✓ Archivos estáticos recolectados"

################################################################################
# 8. CONFIGURAR GUNICORN
################################################################################

print_section "8. CONFIGURANDO GUNICORN"

# Crear archivo de configuración de Gunicorn
print_message "Creando configuración de Gunicorn..."

sudo tee /etc/supervisor/conf.d/gunicorn.conf > /dev/null <<EOF
[program:gunicorn]
directory=$PROJECT_DIR
command=$VENV_DIR/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 $APP_NAME.wsgi:application
autostart=true
autorestart=true
stderr_logfile=/var/log/gunicorn/gunicorn.err.log
stdout_logfile=/var/log/gunicorn/gunicorn.out.log
user=ubuntu
environment=PATH="$VENV_DIR/bin"

[group:guni]
programs:gunicorn
EOF

# Crear directorio para logs
sudo mkdir -p /var/log/gunicorn
sudo chown -R ubuntu:ubuntu /var/log/gunicorn

print_message "✓ Gunicorn configurado"

################################################################################
# 9. CONFIGURAR NGINX
################################################################################

print_section "9. CONFIGURANDO NGINX"

# Obtener el dominio o IP pública
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "0.0.0.0")
print_message "IP pública detectada: $PUBLIC_IP"

# Crear configuración de Nginx
print_message "Creando configuración de Nginx..."

sudo tee /etc/nginx/sites-available/django > /dev/null <<EOF
# Configuración de Nginx para Django + Gunicorn

upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name $PUBLIC_IP notificct.dpdns.org *.notificct.dpdns.org;

    client_max_body_size 100M;

    # Redirigir a HTTPS (se activará después de obtener certificado SSL)
    # return 301 https://\$server_name\$request_uri;

    # Archivos estáticos
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Archivos de media
    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
    }

    # Health check (sin autenticación)
    location /api/health/ {
        proxy_pass http://django;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Proxy a Django/Gunicorn
    location / {
        proxy_pass http://django;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;

        # WebSocket support (si lo necesitas en el futuro)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Habilitar el sitio
sudo ln -sf /etc/nginx/sites-available/django /etc/nginx/sites-enabled/

# Remover configuración por defecto
sudo rm -f /etc/nginx/sites-enabled/default

# Verificar configuración de Nginx
print_message "Verificando configuración de Nginx..."
sudo nginx -t

print_message "✓ Nginx configurado"

################################################################################
# 10. CONFIGURAR FIREWALL (UFW)
################################################################################

print_section "10. CONFIGURANDO FIREWALL (UFW)"

print_message "Configurando reglas de firewall..."
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 8000/tcp   # Gunicorn (opcional, para debugging)

# Habilitar UFW si no está activo (con confirmación automática)
sudo ufw --force enable

print_message "✓ Firewall configurado"

################################################################################
# 11. INICIAR SERVICIOS
################################################################################

print_section "11. INICIANDO SERVICIOS"

# Recargar configuración de Supervisor
print_message "Recargando Supervisor..."
sudo supervisorctl reread
sudo supervisorctl update

# Reiniciar Gunicorn
print_message "Reiniciando Gunicorn..."
sudo supervisorctl restart gunicorn

# Reiniciar Nginx
print_message "Reiniciando Nginx..."
sudo systemctl restart nginx

# Habilitar servicios al inicio
sudo systemctl enable supervisor
sudo systemctl enable nginx

print_message "✓ Servicios iniciados"

################################################################################
# 12. VERIFICAR ESTADO DE SERVICIOS
################################################################################

print_section "12. VERIFICANDO ESTADO DE SERVICIOS"

print_message "Estado de Gunicorn:"
sudo supervisorctl status gunicorn

print_message "Estado de Nginx:"
sudo systemctl status nginx --no-pager | head -10

################################################################################
# 13. CONFIGURAR SSL (OPCIONAL)
################################################################################

print_section "13. CONFIGURACIÓN SSL (Certbot)"

print_warning "Para habilitar SSL/HTTPS, ejecuta manualmente:"
echo ""
echo "sudo certbot --nginx -d notificct.dpdns.org -d *.notificct.dpdns.org"
echo ""
print_warning "IMPORTANTE: Asegúrate de que tu dominio apunte a esta IP: $PUBLIC_IP"

################################################################################
# 14. RESUMEN FINAL
################################################################################

print_section "✅ DESPLIEGUE COMPLETADO"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Backend desplegado exitosamente${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo "📍 URLs de acceso:"
echo "   - HTTP: http://$PUBLIC_IP/api/health/"
echo "   - HTTP: http://notificct.dpdns.org/api/health/"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Verifica que el backend responda: curl http://$PUBLIC_IP/api/health/"
echo "   2. Configura SSL con certbot (ver sección 13)"
echo "   3. Actualiza las variables de entorno en Vercel para el frontend:"
echo "      VITE_API_URL=https://notificct.dpdns.org/api"
echo "   4. Configura Route 53 para apuntar tu dominio a esta IP: $PUBLIC_IP"
echo ""
echo "🔧 Comandos útiles:"
echo "   - Ver logs de Gunicorn: sudo tail -f /var/log/gunicorn/gunicorn.err.log"
echo "   - Ver logs de Nginx: sudo tail -f /var/log/nginx/error.log"
echo "   - Reiniciar Gunicorn: sudo supervisorctl restart gunicorn"
echo "   - Reiniciar Nginx: sudo systemctl restart nginx"
echo "   - Estado de servicios: sudo supervisorctl status"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

################################################################################
# FIN DEL SCRIPT
################################################################################