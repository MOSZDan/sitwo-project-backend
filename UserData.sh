#!/bin/bash
set -e

# --------------------------------------
# CONFIGURACIÓN BÁSICA
# --------------------------------------
REPO_URL="https://github.com/MOSZDan/sitwo-project-backend.git"
PROJECT_DIR="/home/ubuntu/sitwo-project-backend"
VENV_DIR="$PROJECT_DIR/venv"

# --------------------------------------
# ACTUALIZAR O CLONAR EL REPO
# --------------------------------------
if [ -d "$PROJECT_DIR/.git" ]; then
  echo "📦 Proyecto encontrado, actualizando..."
  cd "$PROJECT_DIR"
  git reset --hard
  git pull origin main || git pull origin master
else
  echo "🆕 Clonando proyecto..."
  git clone "$REPO_URL" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
fi

# --------------------------------------
# DEPENDENCIAS DEL SISTEMA
# --------------------------------------
echo "⚙️ Instalando dependencias del sistema..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv nginx git

# --------------------------------------
# CREAR O REUTILIZAR EL ENTORNO VIRTUAL
# --------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  echo "🪄 Creando entorno virtual..."
  python3 -m venv "$VENV_DIR"
else
  echo "♻️ Entorno virtual encontrado, reusando..."
fi

# Activar el entorno
echo "📦 Activando entorno virtual..."
source "$VENV_DIR/bin/activate"

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias del proyecto
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
  echo "📥 Instalando dependencias del proyecto..."
  pip install -r "$PROJECT_DIR/requirements.txt"
fi

# --------------------------------------
# DAR PERMISOS A LOS SCRIPTS Y EJECUTARLOS
# --------------------------------------
echo "🔑 Dando permisos a scripts..."
chmod +x "$PROJECT_DIR"/scripts/*.sh

echo "⚙️ Ejecutando configuración del sistema..."
"$PROJECT_DIR"/scripts/instance_os_dependencies.sh

echo "🐍 Instalando dependencias Python..."
"$PROJECT_DIR"/scripts/python_dependencies.sh

echo "🧠 Configurando Gunicorn..."
"$PROJECT_DIR"/scripts/gunicorn.sh

echo "🌐 Configurando Nginx..."
"$PROJECT_DIR"/scripts/nginx.sh

echo "🚀 Iniciando la aplicación..."
"$PROJECT_DIR"/scripts/start_app.sh

# --------------------------------------
# FIN DEL DEPLOY
# --------------------------------------
echo "✅ Despliegue completado exitosamente."
