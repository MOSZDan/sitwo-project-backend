#!/usr/bin/bash
set -e

echo "=============================="
echo "🚀 Actualizando Backend Django (EC2)"
echo "=============================="

# Ruta base del proyecto
PROJECT_DIR="/home/ubuntu/sitwo-project-backend"

cd "$PROJECT_DIR"

echo "📦 Activando entorno virtual..."
source venv/bin/activate

echo "🔄 Actualizando código desde GitHub..."
git fetch origin
git pull origin main || git pull origin master

echo "📘 Instalando dependencias..."
pip install -r requirements.txt

echo "🧱 Aplicando migraciones..."
python manage.py migrate --noinput

echo "🎨 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "⚙️ Reiniciando servicios..."
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl restart nginx

echo "✅ Estado de los servicios:"
sudo systemctl status gunicorn --no-pager | head -n 10
sudo systemctl status nginx --no-pager | head -n 10

echo "✅ Actualización completada correctamente."
