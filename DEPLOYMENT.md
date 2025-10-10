# Guía de Despliegue - Dental Clinic Backend Multi-Tenant

## Resumen del Problema Identificado

### Problemas encontrados:
1. **Health Check Fallando (400)**: El endpoint `/api/health/` estaba retornando 400 cuando el load balancer hacía health checks sin tenant
2. **Falta Registro DNS Wildcard**: No existía el registro `*.notificct.dpdns.org` para subdominios multi-tenant
3. **Configuración incompleta de Nginx/Gunicorn** en EC2

### Soluciones Aplicadas:
1. Modificado el endpoint `/api/health/` para siempre retornar 200 OK
2. Agregado registro wildcard `*.notificct.dpdns.org` en Route 53 apuntando al load balancer
3. Creados archivos de configuración para Nginx y Gunicorn

---

## Arquitectura del Despliegue

```
Internet
    ↓
Route 53 (DNS)
    ├── notificct.dpdns.org → ALB
    └── *.notificct.dpdns.org → ALB (wildcard para tenants)
    ↓
Application Load Balancer (us-east-2)
    ├── Health Check: /api/health/
    └── Target Group: EC2 Instance (puerto 80)
    ↓
EC2 Instance (t2.micro - Ubuntu)
    ├── Nginx (puerto 80)
    │   ├── Archivos estáticos /static/
    │   ├── Archivos media /media/
    │   └── Proxy a Gunicorn
    ↓
Gunicorn (Unix Socket)
    └── Django App (Multi-Tenant)
    ↓
PostgreSQL (Supabase)
```

---

## Pre-requisitos

1. Instancia EC2 con Ubuntu 20.04+ corriendo
2. Clave SSH (`dental_clinic_backend.pem`) configurada
3. Archivo `.env` con las variables de entorno necesarias
4. Base de datos PostgreSQL (Supabase) configurada

---

## Pasos de Despliegue

### 1. Conectarse a la instancia EC2

```bash
# Desde tu máquina local
ssh -i "dental_clinic_backend.pem" ubuntu@18.220.214.178
```

### 2. Clonar o actualizar el repositorio

```bash
cd /home/ubuntu
# Si es la primera vez:
git clone https://github.com/tu-usuario/sitwo-project-backend.git

# Si ya existe:
cd sitwo-project-backend
git pull origin master
```

### 3. Configurar variables de entorno

Crea el archivo `.env` en la raíz del proyecto:

```bash
nano /home/ubuntu/sitwo-project-backend/.env
```

Copia el contenido de `.env.example` y ajusta las variables:

```env
DJANGO_SECRET_KEY=tu-clave-secreta-super-segura-aqui
DEBUG=False

DB_NAME=postgres
DB_USER=postgres.xxxxx
DB_PASSWORD=tu-password-de-supabase
DB_HOST=aws-0-us-east-2.pooler.supabase.com
DB_PORT=6543

AWS_ACCESS_KEY_ID=tu-aws-access-key-aqui
AWS_SECRET_ACCESS_KEY=tu-aws-secret-key-aqui
AWS_STORAGE_BUCKET_NAME=tu-bucket-s3

STRIPE_PUBLIC_KEY=pk_test_xxxxx
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PRICE_ID=price_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

EMAIL_HOST_PASSWORD=tu-api-key-de-resend
```

### 4. Ejecutar script de despliegue

```bash
cd /home/ubuntu/sitwo-project-backend
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

El script hará:
- Instalar dependencias del sistema
- Crear entorno virtual de Python
- Instalar dependencias de Python
- Ejecutar migraciones
- Recolectar archivos estáticos
- Configurar Nginx
- Configurar y arrancar Gunicorn

### 5. Verificar estado de los servicios

```bash
# Verificar Gunicorn
sudo systemctl status gunicorn

# Verificar Nginx
sudo systemctl status nginx

# Ver logs de Gunicorn
sudo journalctl -u gunicorn -f

# Ver logs de Nginx
sudo tail -f /var/log/nginx/dental_clinic_error.log
```

### 6. Verificar health checks del load balancer

```bash
# Desde tu máquina local o desde la instancia EC2:
curl http://18.220.214.178/api/health/
# Debería retornar: {"ok": true, "status": "healthy", ...}
```

Verifica en AWS Console que el target group esté "healthy":
```bash
aws elbv2 describe-target-health \
  --region us-east-2 \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-2:562291403813:targetgroup/tarjetin/7347d64e8cf887f4
```

---

## Configuración DNS (Ya Aplicada)

El registro wildcard en Route 53 ya está configurado:

- **Dominio principal**: `notificct.dpdns.org` → Load Balancer
- **Wildcard**: `*.notificct.dpdns.org` → Load Balancer

Esto permite que cualquier subdominio (ej: `empresa1.notificct.dpdns.org`, `empresa2.notificct.dpdns.org`) apunte al load balancer.

---

## Crear Tenants (Empresas)

### Desde Django Admin

1. Accede a: `https://notificct.dpdns.org/admin/`
2. Login con tu superusuario
3. Ve a "Empresas" y crea una nueva empresa:
   - Nombre: "Clínica Norte"
   - Subdominio: "norte"
   - Activo: ✓

### Desde la API Pública

```bash
curl -X POST https://notificct.dpdns.org/api/public/registrar-empresa/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Clínica Norte",
    "subdomain": "norte",
    "email_admin": "admin@norte.com",
    "nombre_admin": "Admin",
    "apellido_admin": "Norte",
    "password_admin": "password123"
  }'
```

### Con Stripe (Pago)

```bash
curl -X POST https://notificct.dpdns.org/api/public/registrar-empresa-pago/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Clínica Sur",
    "subdomain": "sur",
    "email_admin": "admin@sur.com",
    "nombre_admin": "Admin",
    "apellido_admin": "Sur",
    "password_admin": "password123",
    "payment_method_id": "pm_card_visa"
  }'
```

---

## Probar Multi-Tenant

### 1. Registrar una empresa
```bash
curl -X POST https://notificct.dpdns.org/api/public/registrar-empresa/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Clínica Test",
    "subdomain": "test",
    "email_admin": "admin@test.com",
    "nombre_admin": "Admin",
    "apellido_admin": "Test",
    "password_admin": "test123"
  }'
```

### 2. Login desde el subdominio
```bash
curl -X POST https://test.notificct.dpdns.org/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "correoelectronico": "admin@test.com",
    "password": "test123"
  }'
```

### 3. Acceder a datos del tenant
```bash
# Obtener token del paso anterior y usarlo
curl -H "Authorization: Token tu-token-aqui" \
  https://test.notificct.dpdns.org/api/pacientes/
```

---

## Troubleshooting

### Health check fallando
```bash
# Ver logs de Gunicorn
sudo journalctl -u gunicorn -n 50

# Ver logs de Nginx
sudo tail -f /var/log/nginx/dental_clinic_error.log

# Probar endpoint directamente
curl -v http://localhost/api/health/
```

### Nginx no arranca
```bash
# Verificar configuración
sudo nginx -t

# Ver logs
sudo tail -f /var/log/nginx/error.log
```

### Gunicorn no arranca
```bash
# Ver logs detallados
sudo journalctl -u gunicorn -xe

# Reiniciar servicio
sudo systemctl restart gunicorn
```

### Base de datos no conecta
```bash
# Probar conexión desde EC2
psql "postgresql://user:password@host:port/database?sslmode=require"

# Ver logs de Django
cd /home/ubuntu/sitwo-project-backend
source venv/bin/activate
python manage.py shell
>>> from django.db import connection
>>> connection.cursor()
```

### Archivos estáticos no se cargan
```bash
# Recolectar estáticos manualmente
cd /home/ubuntu/sitwo-project-backend
source venv/bin/activate
python manage.py collectstatic --noinput

# Verificar permisos
ls -la staticfiles/
sudo chown -R www-data:www-data staticfiles/
```

---

## Comandos Útiles

```bash
# Reiniciar todos los servicios
sudo systemctl restart gunicorn && sudo systemctl restart nginx

# Ver logs en tiempo real
sudo journalctl -u gunicorn -f

# Ejecutar migraciones
cd /home/ubuntu/sitwo-project-backend
source venv/bin/activate
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Abrir shell de Django
python manage.py shell

# Ver estado del load balancer
aws elbv2 describe-target-health --region us-east-2 \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-2:562291403813:targetgroup/tarjetin/7347d64e8cf887f4
```

---

## Información de la Infraestructura

### AWS Resources
- **Región**: us-east-2 (Ohio)
- **EC2 Instance**: i-0d5ce9e883fb7a688 (t2.micro)
- **Public IP**: 18.220.214.178
- **Load Balancer**: balancearin-1841542738.us-east-2.elb.amazonaws.com
- **Target Group**: tarjetin (puerto 80, health check: /api/health/)
- **Route 53 Zone**: Z0106742VGOVI7LSMCBM
- **Dominio**: notificct.dpdns.org

### Puertos
- **80**: HTTP (Nginx)
- **443**: HTTPS (Load Balancer)
- **8000**: Django/Gunicorn (via Unix socket)

---

## Seguridad

**IMPORTANTE**: Después de completar el despliegue, debes:

1. **Rotar credenciales de AWS** periódicamente:
   ```bash
   aws iam create-access-key --user-name tu-usuario
   ```

2. **Configurar HTTPS** en el load balancer (ya tienes certificado ACM)

3. **Configurar Security Groups** para restringir acceso SSH solo a tu IP

4. **Habilitar backups** de la base de datos

5. **Configurar CloudWatch** para monitoreo y alertas

---

## Próximos Pasos

1. Configurar certificado SSL/TLS (ya existe en ACM)
2. Implementar CI/CD con GitHub Actions
3. Configurar backups automáticos
4. Implementar monitoreo con CloudWatch
5. Configurar auto-scaling si es necesario
6. Implementar CDN (CloudFront) para archivos estáticos

---

## Contacto y Soporte

Para problemas o consultas, revisa los logs y la documentación de Django en:
- https://docs.djangoproject.com/
- https://docs.gunicorn.org/
- https://nginx.org/en/docs/