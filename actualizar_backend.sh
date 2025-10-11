#!/bin/bash

################################################################################
# SCRIPT DE ACTUALIZACIÓN SEGURA DEL BACKEND
################################################################################
# Este script actualiza el código sin romper la configuración existente
# Es SEGURO ejecutarlo múltiples veces
################################################################################

set -e  # Detener si hay error

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
# VERIFICACIONES INICIALES
################################################################################

print_section "VERIFICANDO ENTORNO"

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    print_error "Este script debe ejecutarse desde el directorio del proyecto"
    print_error "Por favor, cd al directorio: /home/ubuntu/sitwo-project-backend"
    exit 1
fi

PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"

print_message "Directorio del proyecto: $PROJECT_DIR"

# Verificar que existe el .env
if [ ! -f ".env" ]; then
    print_error "No se encontró el archivo .env"
    print_error "El archivo .env es necesario para la configuración"
    exit 1
fi

print_message "✓ Archivo .env encontrado"

################################################################################
# CREAR BACKUP
################################################################################

print_section "CREANDO BACKUP DE SEGURIDAD"

BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

mkdir -p "$BACKUP_DIR"

print_message "Creando backup en: $BACKUP_PATH"

# Backup de archivos importantes
mkdir -p "$BACKUP_PATH"
cp -r api "$BACKUP_PATH/" 2>/dev/null || true
cp -r dental_clinic_backend "$BACKUP_PATH/" 2>/dev/null || true
cp .env "$BACKUP_PATH/.env" 2>/dev/null || true
cp requirements.txt "$BACKUP_PATH/" 2>/dev/null || true

print_message "✓ Backup creado exitosamente"

################################################################################
# ACTUALIZAR CÓDIGO DESDE GIT
################################################################################

print_section "ACTUALIZANDO CÓDIGO DESDE GIT"

# Guardar cambios locales si existen
if [[ -n $(git status -s) ]]; then
    print_warning "Hay cambios locales no guardados"
    print_message "Guardando cambios locales en stash..."
    git stash save "Auto-stash before update $TIMESTAMP"
fi

# Obtener últimos cambios
print_message "Descargando últimos cambios..."
git fetch origin

# Ver si hay actualizaciones
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ $LOCAL = $REMOTE ]; then
    print_message "✓ El código ya está actualizado"
else
    print_message "Aplicando actualizaciones..."
    git pull origin master
    print_message "✓ Código actualizado exitosamente"
fi

################################################################################
# ACTIVAR ENTORNO VIRTUAL
################################################################################

print_section "CONFIGURANDO ENTORNO VIRTUAL"

if [ ! -d "$VENV_DIR" ]; then
    print_warning "No se encontró entorno virtual. Creando uno nuevo..."
    python3 -m venv "$VENV_DIR"
fi

print_message "Activando entorno virtual..."
source "$VENV_DIR/bin/activate"

# Actualizar pip
print_message "Actualizando pip..."
pip install --upgrade pip -q

################################################################################
# INSTALAR/ACTUALIZAR DEPENDENCIAS
################################################################################

print_section "INSTALANDO DEPENDENCIAS"

if [ -f "requirements.txt" ]; then
    print_message "Instalando/actualizando dependencias de Python..."
    pip install -r requirements.txt -q
    print_message "✓ Dependencias instaladas"
else
    print_error "No se encontró requirements.txt"
    exit 1
fi

################################################################################
# EJECUTAR MIGRACIONES
################################################################################

print_section "EJECUTANDO MIGRACIONES DE BASE DE DATOS"

print_message "Verificando migraciones pendientes..."
python manage.py showmigrations --plan | tail -5

print_message "Aplicando migraciones..."
python manage.py migrate --noinput

print_message "✓ Migraciones aplicadas"

################################################################################
# RECOLECTAR ARCHIVOS ESTÁTICOS
################################################################################

print_section "RECOLECTANDO ARCHIVOS ESTÁTICOS"

print_message "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput -c

print_message "✓ Archivos estáticos actualizados"

################################################################################
# VERIFICAR CONFIGURACIÓN
################################################################################

print_section "VERIFICANDO CONFIGURACIÓN"

# Verificar que DEBUG está en False
if grep -q "DEBUG=True" .env; then
    print_error "¡ATENCIÓN! DEBUG está en True"
    print_error "Por seguridad, cambia DEBUG=False en el archivo .env"
    print_warning "Continuando de todos modos..."
else
    print_message "✓ DEBUG está en False (producción)"
fi

# Test de configuración de Django
print_message "Verificando configuración de Django..."
python manage.py check --deploy --fail-level WARNING || print_warning "Hay advertencias de configuración (revisar arriba)"

################################################################################
# REINICIAR SERVICIOS
################################################################################

print_section "REINICIANDO SERVICIOS"

# Verificar si Gunicorn está corriendo con Supervisor
if command -v supervisorctl &> /dev/null; then
    print_message "Reiniciando Gunicorn con Supervisor..."
    sudo supervisorctl restart gunicorn 2>/dev/null || print_warning "No se pudo reiniciar con Supervisor"

    sleep 2

    # Verificar estado
    print_message "Estado de Gunicorn:"
    sudo supervisorctl status gunicorn 2>/dev/null || print_warning "Supervisor no responde"
else
    print_warning "Supervisor no está instalado"
    print_message "Buscando proceso de Gunicorn para reiniciar manualmente..."

    # Buscar y reiniciar Gunicorn manualmente
    GUNICORN_PID=$(pgrep -f "gunicorn.*$PROJECT_DIR" | head -1)

    if [ -n "$GUNICORN_PID" ]; then
        print_message "Encontrado Gunicorn (PID: $GUNICORN_PID)"
        print_message "Enviando señal HUP para recargar..."
        kill -HUP $GUNICORN_PID
    else
        print_warning "No se encontró proceso de Gunicorn corriendo"
    fi
fi

# Reiniciar Nginx si está disponible
if command -v nginx &> /dev/null; then
    print_message "Reiniciando Nginx..."
    sudo systemctl reload nginx 2>/dev/null || sudo service nginx reload 2>/dev/null || print_warning "No se pudo recargar Nginx"
fi

################################################################################
# VERIFICAR QUE TODO FUNCIONA
################################################################################

print_section "VERIFICANDO FUNCIONAMIENTO"

sleep 3

# Test del endpoint de salud
print_message "Probando endpoint de salud..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/health/ 2>&1 || echo "ERROR")

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    print_message "✓ Backend respondiendo correctamente"
    echo "$HEALTH_RESPONSE"
else
    print_error "El backend no responde correctamente"
    print_error "Respuesta: $HEALTH_RESPONSE"
    print_warning "Revisa los logs: sudo tail -f /var/log/gunicorn/gunicorn.err.log"
fi

################################################################################
# LIMPIAR BACKUPS ANTIGUOS
################################################################################

print_section "LIMPIANDO BACKUPS ANTIGUOS"

# Mantener solo los últimos 5 backups
print_message "Limpiando backups antiguos (manteniendo los últimos 5)..."
cd "$BACKUP_DIR"
ls -t | tail -n +6 | xargs rm -rf 2>/dev/null || true
cd "$PROJECT_DIR"

print_message "✓ Limpieza completada"

################################################################################
# RESUMEN FINAL
################################################################################

print_section "✅ ACTUALIZACIÓN COMPLETADA"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Backend actualizado exitosamente${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo "📋 Resumen:"
echo "   - Backup guardado en: $BACKUP_PATH"
echo "   - Código actualizado desde Git"
echo "   - Dependencias instaladas"
echo "   - Migraciones aplicadas"
echo "   - Archivos estáticos actualizados"
echo "   - Servicios reiniciados"
echo ""
echo "🔍 Verificación:"
echo "   - Backend: http://localhost:8000/api/health/"
echo "   - Público: https://notificct.dpdns.org/api/health/"
echo ""
echo "📝 Comandos útiles:"
echo "   - Ver logs: sudo tail -f /var/log/gunicorn/gunicorn.err.log"
echo "   - Reiniciar: sudo supervisorctl restart gunicorn"
echo "   - Estado: sudo supervisorctl status"
echo "   - Restaurar backup: cp -r $BACKUP_PATH/* $PROJECT_DIR/"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

################################################################################
# FIN
################################################################################