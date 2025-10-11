# 🚀 Guía Completa de Despliegue en AWS EC2 + Route 53

Esta guía te ayudará a desplegar tu sistema dental SaaS multi-tenant en AWS EC2 de forma automatizada.

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Problema Identificado](#problema-identificado)
3. [Solución Implementada](#solución-implementada)
4. [Paso a Paso: Despliegue en EC2](#paso-a-paso-despliegue-en-ec2)
5. [Configurar Route 53 (DNS)](#configurar-route-53-dns)
6. [Configurar Variables de Entorno en Vercel](#configurar-variables-de-entorno-en-vercel)
7. [Verificación y Troubleshooting](#verificación-y-troubleshooting)
8. [Mantenimiento](#mantenimiento)

---

## 📝 Requisitos Previos

Antes de comenzar, asegúrate de tener:

- ✅ Cuenta de AWS activa
- ✅ Instancia EC2 Ubuntu 22.04 creada y corriendo
- ✅ Key pair (.pem) para conectarte a EC2
- ✅ Security Group configurado con puertos 22, 80, 443, 8000 abiertos
- ✅ Base de datos PostgreSQL (Supabase o RDS)
- ✅ Bucket S3 para almacenamiento de archivos
- ✅ Cuenta de Stripe configurada
- ✅ Dominio registrado (ej: notificct.dpdns.org)

---

## 🔍 Problema Identificado

### Error: "No se pudo verificar la disponibilidad. Intenta de nuevo"

**Causa raíz identificada:**

1. **CORS Configuration Issue**: El frontend en Vercel no podía comunicarse con el backend
2. **URL del API incorrecta**: El frontend apuntaba a `/api` en lugar de la URL real del backend
3. **Falta de configuración en producción**: Variables de entorno no configuradas correctamente

**Archivos afectados:**

- `dental_clinic_backend/settings.py` (líneas 42-85)
- `BuyDental/.env` (líneas 15, 23)

---

## ✅ Solución Implementada

### 1. **Backend (`settings.py`)**

Se actualizó la configuración de CORS para permitir:
- Subdominios wildcard de Vercel
- Dominios locales para desarrollo
- Dominio principal de producción

```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.dpdns\.org$",
    r"^https://[\w-]+\.notificct\.dpdns\.org$",
    r"^https://[\w-]+\.vercel\.app$",  # Vercel deployments
    r"^http://localhost:\d+$",  # Desarrollo local
]
```

### 2. **Frontend (`.env`)**

Se actualizó la URL del API para apuntar al backend en producción:

```bash
VITE_API_URL=https://notificct.dpdns.org/api
VITE_BASE_DOMAIN=notificct.dpdns.org
```

### 3. **Scripts de Despliegue Automatizados**

Se crearon dos scripts:
- `deploy_to_aws.sh`: Despliegue completo del backend
- `setup_route53.sh`: Configuración automática de DNS

---

## 🚀 Paso a Paso: Despliegue en EC2

### Paso 1: Conectarse a tu instancia EC2

```bash
# Desde tu terminal local
ssh -i "tu-llave.pem" ubuntu@tu-ip-publica-ec2
```

**Ejemplo:**
```bash
ssh -i "mi-key.pem" ubuntu@18.220.214.178
```

### Paso 2: Clonar el repositorio

```bash
cd /home/ubuntu
git clone <url-de-tu-repositorio> sitwo-project-backend
cd sitwo-project-backend
```

Si no tienes Git configurado:
```bash
# Instalar Git
sudo apt-get update
sudo apt-get install -y git

# Configurar Git
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
```

### Paso 3: Crear archivo .env con tus credenciales

```bash
nano .env
```

**Contenido del archivo .env:**

```bash
# CONFIGURACION GENERAL
DEBUG=False
DJANGO_SECRET_KEY=tu-secret-key-super-segura-generada-aleatoriamente
FRONTEND_URL=https://buy-dental-smile.vercel.app

# BASE DE DATOS (PostgreSQL)
DB_NAME=tu_base_de_datos
DB_USER=tu_usuario
DB_PASSWORD=tu_password_seguro
DB_HOST=tu-proyecto.supabase.co
DB_PORT=5432

# AWS S3 (Almacenamiento)
AWS_ACCESS_KEY_ID=tu_access_key_de_aws
AWS_SECRET_ACCESS_KEY=tu_secret_key_de_aws
AWS_STORAGE_BUCKET_NAME=tu-bucket-s3

# STRIPE (Pagos)
STRIPE_SECRET_KEY=sk_test_tu_stripe_secret_key
STRIPE_PUBLIC_KEY=pk_test_tu_stripe_public_key
STRIPE_PRICE_ID=price_tu_price_id
STRIPE_WEBHOOK_SECRET=whsec_tu_webhook_secret

# EMAIL (Opcional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**Guardar:** `Ctrl + O`, luego `Enter`, luego `Ctrl + X`

### Paso 4: Dar permisos de ejecución al script

```bash
chmod +x deploy_to_aws.sh
```

### Paso 5: Ejecutar el script de despliegue

```bash
./deploy_to_aws.sh
```

Este script hará **automáticamente**:

1. ✅ Actualizar sistema operativo
2. ✅ Instalar Python 3.11, Nginx, Supervisor
3. ✅ Crear entorno virtual de Python
4. ✅ Instalar dependencias del proyecto
5. ✅ Ejecutar migraciones de base de datos
6. ✅ Recolectar archivos estáticos
7. ✅ Configurar Gunicorn
8. ✅ Configurar Nginx
9. ✅ Configurar firewall (UFW)
10. ✅ Iniciar todos los servicios

**Tiempo estimado:** 5-10 minutos

### Paso 6: Verificar que todo funciona

```bash
# Verificar estado de servicios
sudo supervisorctl status

# Debería mostrar:
# gunicorn    RUNNING   pid 12345, uptime 0:00:30

# Verificar Nginx
sudo systemctl status nginx

# Probar el endpoint de salud
curl http://localhost:8000/api/health/
```

**Respuesta esperada:**
```json
{"status": "healthy", "database": "connected"}
```

---

## 🌐 Configurar Route 53 (DNS)

### Opción 1: Script Automatizado (Recomendado)

```bash
# Dar permisos de ejecución
chmod +x setup_route53.sh

# Ejecutar script
./setup_route53.sh
```

El script te pedirá:
1. Nombre de dominio (ej: `notificct.dpdns.org`)
2. IP pública de tu EC2 (ej: `18.220.214.178`)
3. AWS Access Key ID
4. AWS Secret Access Key

### Opción 2: Manual desde AWS Console

1. Ve a **Route 53** en AWS Console
2. Crea una **Hosted Zone** para tu dominio
3. Crea dos registros:
   - **Registro A**: `notificct.dpdns.org` → IP de tu EC2
   - **Registro A wildcard**: `*.notificct.dpdns.org` → IP de tu EC2

---

## 🔒 Configurar SSL (HTTPS)

Una vez que tu dominio esté propagado:

```bash
# Instalar certificado SSL con Certbot
sudo certbot --nginx -d notificct.dpdns.org -d *.notificct.dpdns.org

# Seguir las instrucciones en pantalla
# Certbot configurará automáticamente Nginx para HTTPS
```

**Nota:** Para wildcard SSL necesitas validación DNS. Certbot te dará instrucciones específicas.

---

## 🎨 Configurar Variables de Entorno en Vercel

### Paso 1: Ir al Dashboard de Vercel

1. Ve a [vercel.com](https://vercel.com)
2. Selecciona tu proyecto **buy-dental-smile**
3. Ve a **Settings** → **Environment Variables**

### Paso 2: Agregar/Actualizar Variables

Agrega estas variables:

```bash
VITE_API_URL=https://notificct.dpdns.org/api
VITE_BASE_DOMAIN=notificct.dpdns.org
VITE_FRONTEND_URL=https://buy-dental-smile.vercel.app
VITE_STRIPE_PUBLIC_KEY=pk_test_tu_stripe_public_key
```

### Paso 3: Re-desplegar

Después de guardar las variables, Vercel re-desplegará automáticamente.

---

## ✅ Verificación y Troubleshooting

### 1. Verificar Backend

```bash
# Desde tu máquina local
curl https://notificct.dpdns.org/api/health/

# Debería responder:
{"status": "healthy", "database": "connected"}
```

### 2. Verificar DNS

```bash
# Verificar propagación DNS
nslookup notificct.dpdns.org

# O usar una herramienta online:
# https://dnschecker.org
```

### 3. Verificar Frontend

Abre en tu navegador:
```
https://buy-dental-smile.vercel.app
```

Prueba registrar una empresa con un subdominio.

### 4. Ver Logs

```bash
# Logs de Gunicorn
sudo tail -f /var/log/gunicorn/gunicorn.err.log

# Logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Logs de Django
cd /home/ubuntu/sitwo-project-backend
source venv/bin/activate
python manage.py runserver  # Solo para debugging, no en producción
```

### Problemas Comunes

#### Error: "No se pudo verificar la disponibilidad"

**Solución:**
1. Verifica que el backend esté corriendo: `curl https://notificct.dpdns.org/api/health/`
2. Verifica las variables de entorno en Vercel
3. Revisa los logs de Nginx: `sudo tail -f /var/log/nginx/error.log`

#### Error 502 Bad Gateway

**Solución:**
```bash
# Reiniciar Gunicorn
sudo supervisorctl restart gunicorn

# Si persiste, revisar logs
sudo tail -f /var/log/gunicorn/gunicorn.err.log
```

#### Error de CORS

**Solución:**
1. Verifica que el dominio esté en `CORS_ALLOWED_ORIGINS` en `settings.py`
2. Reinicia Gunicorn: `sudo supervisorctl restart gunicorn`

---

## 🔧 Mantenimiento

### Actualizar el código

```bash
# Conectarse a EC2
ssh -i "tu-llave.pem" ubuntu@tu-ip-ec2

# Ir al directorio del proyecto
cd /home/ubuntu/sitwo-project-backend

# Activar entorno virtual
source venv/bin/activate

# Pull de los últimos cambios
git pull origin master

# Instalar nuevas dependencias (si las hay)
pip install -r requirements.txt

# Ejecutar migraciones
python manage.py migrate

# Recolectar estáticos
python manage.py collectstatic --noinput

# Reiniciar servicios
sudo supervisorctl restart gunicorn
sudo systemctl restart nginx
```

### Reiniciar servicios manualmente

```bash
# Reiniciar Gunicorn
sudo supervisorctl restart gunicorn

# Reiniciar Nginx
sudo systemctl restart nginx

# Ver estado de todos los servicios
sudo supervisorctl status
```

### Backup de base de datos

```bash
# Backup manual
pg_dump -h tu-host.supabase.co -U tu-usuario -d tu-base-datos > backup_$(date +%Y%m%d).sql
```

---

## 🔐 Seguridad: IMPORTANTE

### ⚠️ REVOCA LAS CREDENCIALES EXPUESTAS

**Si compartiste credenciales AWS públicamente**, debes **INMEDIATAMENTE**:

1. Ve a AWS Console → IAM → Users → Security Credentials
2. Encuentra y revoca las Access Keys expuestas
3. **Desactiva** o **Elimina** esas credenciales
4. Genera nuevas credenciales
5. Actualiza el archivo `.env` con las nuevas credenciales

**Nunca compartas:**
- AWS Access Keys
- Secret Keys
- Claves de Stripe SECRET (sk_...)
- Contraseñas de base de datos
- DJANGO_SECRET_KEY

---

## 📞 Soporte

Si encuentras algún problema:

1. Revisa los logs: `sudo tail -f /var/log/gunicorn/gunicorn.err.log`
2. Verifica la configuración: `cat .env`
3. Prueba los endpoints manualmente: `curl http://localhost:8000/api/health/`

---

## 🎉 ¡Listo!

Tu sistema dental SaaS multi-tenant ya está desplegado en AWS EC2 con:

✅ Backend Django en EC2
✅ Frontend React en Vercel
✅ DNS configurado con Route 53
✅ SSL/HTTPS con Certbot
✅ Base de datos PostgreSQL
✅ Almacenamiento en S3
✅ Pagos con Stripe

**URLs finales:**
- Backend API: `https://notificct.dpdns.org/api/`
- Frontend: `https://buy-dental-smile.vercel.app`
- Admin Django: `https://notificct.dpdns.org/admin/`

---

## 📚 Recursos Adicionales

- [Documentación Django](https://docs.djangoproject.com/)
- [AWS EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [Route 53 Documentation](https://docs.aws.amazon.com/route53/)
- [Certbot Documentation](https://certbot.eff.org/)
- [Vercel Documentation](https://vercel.com/docs)

---

**Fecha de creación:** 2025-10-11
**Versión:** 1.0
**Autor:** Claude Code Assistant