#!/bin/bash
# Script para desplegar cambios en EC2

set -e

echo "=========================================="
echo "DESPLEGANDO CAMBIOS EN EC2"
echo "=========================================="

# Variables
EC2_HOST="18.220.214.178"
EC2_USER="ubuntu"
PROJECT_DIR="/home/ubuntu/sitwo-project-backend"

echo ""
echo "1. Conectando con EC2..."
ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} << 'ENDSSH'

echo "2. Navegando al directorio del proyecto..."
cd /home/ubuntu/sitwo-project-backend

echo "3. Haciendo git pull para obtener últimos cambios..."
git pull origin master

echo "4. Activando entorno virtual..."
source venv/bin/activate

echo "5. Instalando/actualizando dependencias..."
pip install -r requirements.txt

echo "6. Ejecutando migraciones..."
python manage.py migrate --noinput

echo "7. Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "8. Reiniciando servicios..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx

echo ""
echo "=========================================="
echo "DESPLIEGUE COMPLETADO"
echo "=========================================="

echo ""
echo "Verificando estado de servicios:"
sudo systemctl status gunicorn --no-pager | head -3
sudo systemctl status nginx --no-pager | head -3

ENDSSH

echo ""
echo "Listo! El servidor ha sido actualizado."
echo "Puedes verificar en: http://notificct.dpdns.org/api/health/"