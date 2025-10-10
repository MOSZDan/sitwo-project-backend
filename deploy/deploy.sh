#!/bin/bash
# Script de despliegue para Dental Clinic Backend
# Ejecutar en la instancia EC2 como usuario ubuntu

set -e  # Detener en caso de error

echo "==================================="
echo "Dental Clinic Backend - Despliegue"
echo "==================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables
PROJECT_DIR="/home/ubuntu/sitwo-project-backend"
VENV_DIR="$PROJECT_DIR/venv"
REPO_URL="https://github.com/tu-usuario/sitwo-project-backend.git"

echo -e "${YELLOW}[1/10] Actualizando sistema...${NC}"
sudo apt-get update

echo -e "${YELLOW}[2/10] Instalando dependencias del sistema...${NC}"
sudo apt-get install -y python3-pip python3-venv nginx postgresql-client git

echo -e "${YELLOW}[3/10] Verificando directorio del proyecto...${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Clonando repositorio..."
    cd /home/ubuntu
    git clone $REPO_URL sitwo-project-backend
else
    echo "Actualizando código..."
    cd $PROJECT_DIR
    git pull origin master
fi

cd $PROJECT_DIR

echo -e "${YELLOW}[4/10] Configurando entorno virtual...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo -e "${YELLOW}[5/10] Instalando dependencias de Python...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

echo -e "${YELLOW}[6/10] Verificando archivo .env...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}ERROR: Archivo .env no encontrado!${NC}"
    echo "Por favor, crea el archivo .env con las variables necesarias."
    exit 1
fi

echo -e "${YELLOW}[7/10] Ejecutando migraciones...${NC}"
python manage.py migrate --noinput

echo -e "${YELLOW}[8/10] Recolectando archivos estáticos...${NC}"
python manage.py collectstatic --noinput --clear

echo -e "${YELLOW}[9/10] Configurando Nginx...${NC}"
sudo cp deploy/nginx.conf /etc/nginx/sites-available/dental_clinic
sudo ln -sf /etc/nginx/sites-available/dental_clinic /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo -e "${YELLOW}[10/10] Configurando Gunicorn...${NC}"
sudo mkdir -p /var/log/gunicorn
sudo chown -R ubuntu:www-data /var/log/gunicorn
sudo cp deploy/gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn

echo -e "${GREEN}✓ Despliegue completado exitosamente!${NC}"
echo ""
echo "Para verificar el estado de los servicios:"
echo "  sudo systemctl status gunicorn"
echo "  sudo systemctl status nginx"
echo ""
echo "Para ver logs:"
echo "  sudo journalctl -u gunicorn -f"
echo "  sudo tail -f /var/log/nginx/dental_clinic_error.log"