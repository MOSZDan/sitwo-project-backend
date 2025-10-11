#!/bin/bash
# Script para actualizar el servidor EC2 con los últimos cambios

set -e  # Detener si hay errores

echo "=================================="
echo "Actualizando servidor EC2..."
echo "=================================="

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
PROJECT_DIR="/home/ubuntu/sitwo-project-backend"
VENV_DIR="$PROJECT_DIR/venv"

cd $PROJECT_DIR

echo -e "${YELLOW}[1/5] Haciendo git pull...${NC}"
git pull origin master

echo -e "${YELLOW}[2/5] Activando entorno virtual...${NC}"
source $VENV_DIR/bin/activate

echo -e "${YELLOW}[3/5] Instalando/actualizando dependencias...${NC}"
pip install -r requirements.txt

echo -e "${YELLOW}[4/5] Ejecutando migraciones...${NC}"
python manage.py migrate --noinput

echo -e "${YELLOW}[5/5] Reiniciando servicios...${NC}"
sudo systemctl restart gunicorn
sudo systemctl restart nginx

echo -e "${GREEN}✓ Actualización completada!${NC}"
echo ""
echo "Verificando estado de servicios:"
sudo systemctl status gunicorn --no-pager | head -10
echo ""
sudo systemctl status nginx --no-pager | head -10