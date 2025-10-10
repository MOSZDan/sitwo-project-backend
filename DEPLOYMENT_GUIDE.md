# 🚀 Guía de Deployment - SaaS Multi-Tenant

## 📋 Resumen

Esta guía te ayudará a desplegar tu sistema multi-tenant SaaS en producción.

---

## 🎯 Arquitectura de Producción

```
                          ┌─────────────────────────┐
                          │   Usuarios Finales      │
                          └──────────┬──────────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     │               │               │
        ┌────────────▼──────┐   ┌───▼────────┐  ┌───▼────────┐
        │  Landing Page      │   │  Tenant 1  │  │  Tenant 2  │
        │  (Público)         │   │  Frontend  │  │  Frontend  │
        │  notificct.        │   │  norte.    │  │  sur.      │
        │  dpdns.org         │   │  notificct │  │  notificct │
        └────────────┬───────┘   └────┬───────┘  └────┬───────┘
                     │                │               │
                     └────────────────┼───────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │   Load Balancer/CDN    │
                          │   (Cloudflare/AWS)     │
                          └───────────┬────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │   Backend API          │
                          │   (Django + DRF)       │
                          │   tu-backend.com       │
                          └───────────┬────────────┘
                                      │
                     ┌────────────────┼────────────────┐
                     │                │                │
        ┌────────────▼───────┐  ┌────▼────────┐  ┌───▼────────┐
        │  PostgreSQL DB     │  │  AWS S3     │  │  Email     │
        │  (RDS/Supabase)    │  │  (Files)    │  │  (Resend)  │
        └────────────────────┘  └─────────────┘  └────────────┘
```

---

## 🗂️ Pre-requisitos

### Cuentas Necesarias:

1. **Hosting Backend**: Render / AWS / DigitalOcean / Railway
2. **Hosting Frontend**: Vercel / Netlify / Cloudflare Pages
3. **Base de Datos**: AWS RDS / Supabase / ElephantSQL
4. **Storage de Archivos**: AWS S3 / Cloudflare R2
5. **Email**: Resend / SendGrid / AWS SES
6. **DNS**: Cloudflare (recomendado) o tu proveedor actual
7. **(Opcional) CDN**: Cloudflare
8. **(Opcional) Monitoring**: Sentry

---

## 📝 Paso 1: Configurar DNS

### Opción A: Cloudflare (Recomendado)

1. Agregar tu dominio a Cloudflare
2. Configurar registros DNS:

```
Tipo: A
Nombre: @
Valor: IP_de_tu_backend
Proxy: Activado (naranja)

Tipo: A
Nombre: *
Valor: IP_de_tu_backend
Proxy: Activado (naranja)
```

**O si usas CNAME para frontend separado:**

```
Tipo: CNAME
Nombre: @
Valor: tu-frontend.vercel.app
Proxy: Activado

Tipo: CNAME
Nombre: *
Valor: tu-frontend.vercel.app
Proxy: Activado
```

### Opción B: AWS Route 53

```bash
# Crear Hosted Zone
aws route53 create-hosted-zone --name notificct.dpdns.org

# Agregar registro wildcard
{
  "Name": "*.notificct.dpdns.org",
  "Type": "A",
  "AliasTarget": {
    "HostedZoneId": "Z123456",
    "DNSName": "tu-alb.us-east-2.elb.amazonaws.com",
    "EvaluateTargetHealth": false
  }
}
```

---

## 🐳 Paso 2: Backend (Django)

### Opción A: Render (Más Fácil)

1. Conectar tu repositorio GitHub
2. Crear nuevo **Web Service**
3. Configurar:

```yaml
Build Command: pip install -r requirements.txt
Start Command: gunicorn dental_clinic_backend.wsgi:application --bind 0.0.0.0:$PORT
```

4. **IMPORTANTE**: Editar `dental_clinic_backend/settings.py` y actualizar las credenciales:
   - `SECRET_KEY`: Generar una nueva clave secreta
   - `DEBUG`: Mantener en `False` para producción
   - `EMAIL_HOST_PASSWORD`: Tu API key de Resend/SendGrid
   - `ONESIGNAL_APP_ID` y `ONESIGNAL_REST_API_KEY` (si usas notificaciones push)
   - Verificar credenciales de AWS S3 y base de datos

5. Deploy

### Opción B: AWS EC2 + Gunicorn + Nginx

```bash
# 1. SSH a tu servidor
ssh ubuntu@tu-ip

# 2. Instalar dependencias
sudo apt update
sudo apt install python3-pip python3-venv nginx postgresql-client

# 3. Clonar proyecto
git clone https://github.com/tu-usuario/tu-repo.git
cd tu-repo

# 4. Crear virtualenv
python3 -m venv venv
source venv/bin/activate

# 5. Instalar dependencias
pip install -r requirements.txt
pip install gunicorn

# 6. Configurar settings.py
nano dental_clinic_backend/settings.py
# Actualizar SECRET_KEY, EMAIL_HOST_PASSWORD, y otras credenciales

# 7. Migraciones
python manage.py migrate
python manage.py collectstatic --noinput

# 8. Crear servicio systemd
sudo nano /etc/systemd/system/dental-backend.service
```

```ini
[Unit]
Description=Dental Clinic Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/tu-repo
Environment="PATH=/home/ubuntu/tu-repo/venv/bin"
ExecStart=/home/ubuntu/tu-repo/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 dental_clinic_backend.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# 9. Iniciar servicio
sudo systemctl start dental-backend
sudo systemctl enable dental-backend

# 10. Configurar Nginx
sudo nano /etc/nginx/sites-available/dental
```

```nginx
server {
    listen 80;
    server_name notificct.dpdns.org *.notificct.dpdns.org;

    location /static/ {
        alias /home/ubuntu/tu-repo/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/tu-repo/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 11. Activar sitio
sudo ln -s /etc/nginx/sites-available/dental /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 12. Configurar SSL (Certbot)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d notificct.dpdns.org -d '*.notificct.dpdns.org'
```

### Opción C: Docker + AWS ECS

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "dental_clinic_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```bash
# Construir y subir a ECR
docker build -t dental-backend .
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-2.amazonaws.com
docker tag dental-backend:latest <account-id>.dkr.ecr.us-east-2.amazonaws.com/dental-backend:latest
docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/dental-backend:latest
```

---

## 🎨 Paso 3: Frontend Público (Landing Page)

### Opción A: Vercel (Recomendado)

1. Push tu código a GitHub
2. Ir a vercel.com
3. Import repository
4. Configurar:

```
Framework Preset: React / Vite
Build Command: npm run build
Output Directory: dist
```

5. Environment Variables:

```
VITE_API_URL=https://tu-backend.com/api
VITE_BASE_DOMAIN=notificct.dpdns.org
```

6. Configurar Dominio:
   - Settings → Domains
   - Add Domain: `notificct.dpdns.org`
   - Vercel te dará instrucciones de DNS

7. Deploy

### Opción B: Netlify

Similar a Vercel:

```bash
# Instalar Netlify CLI
npm install -g netlify-cli

# Build
npm run build

# Deploy
netlify deploy --prod
```

Configurar dominio en Netlify Dashboard.

---

## 🌐 Paso 4: Frontend de Aplicación (Multi-Tenant)

### Configurar Wildcard Subdomain

#### En Vercel:

1. Deploy normalmente
2. Settings → Domains
3. Add Domain: `*.notificct.dpdns.org`
4. Vercel mostrará CNAME a configurar

#### En tu DNS (Cloudflare):

```
Tipo: CNAME
Nombre: *
Valor: cname.vercel-dns.com
Proxy: Desactivado (gris) [IMPORTANTE]
```

### Modificar Código del Frontend

**1. Instalar axios:**

```bash
npm install axios
```

**2. Crear `src/utils/tenant.js`:**

```javascript
export function getTenantFromURL() {
  const host = window.location.host;
  const parts = host.split('.');

  // Desarrollo: localhost
  if (host.includes('localhost')) {
    // Extraer de: norte.localhost:5173
    return parts[0] === 'localhost' ? null : parts[0];
  }

  // Producción: norte.notificct.dpdns.org
  if (parts.length >= 3) {
    return parts[0];
  }

  return null;
}

export function redirectToPublic() {
  window.location.href = 'https://notificct.dpdns.org';
}
```

**3. Crear `src/api/client.js`:**

```javascript
import axios from 'axios';
import { getTenantFromURL, redirectToPublic } from '../utils/tenant';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://tu-backend.com/api',
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const subdomain = getTenantFromURL();

  if (!subdomain && !config.url.startsWith('/public/')) {
    // Si no hay tenant y no es endpoint público, redirigir
    redirectToPublic();
    return Promise.reject('No tenant');
  }

  if (subdomain) {
    config.headers['X-Tenant-Subdomain'] = subdomain;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 404 && error.response?.data?.message?.includes('tenant')) {
      // Empresa no encontrada
      window.location.href = '/empresa-no-encontrada';
    }
    return Promise.reject(error);
  }
);

export default api;
```

**4. Usar en tus componentes:**

```javascript
import api from '../api/client';

// En lugar de:
// const response = await axios.get('/api/pacientes/');

// Usar:
const response = await api.get('/pacientes/');
```

**5. Página de Error (opcional):**

```javascript
// src/pages/EmpresaNoEncontrada.jsx
function EmpresaNoEncontrada() {
  return (
    <div>
      <h1>Empresa no encontrada</h1>
      <p>El subdominio que intentas acceder no existe o está inactivo.</p>
      <a href="https://notificct.dpdns.org">Ir al sitio principal</a>
    </div>
  );
}
```

---

## 🔒 Paso 5: Configurar SSL Wildcard

### Opción A: Cloudflare (Automático)

Si usas Cloudflare como CDN, SSL wildcard es automático. Solo activa:

1. SSL/TLS → Overview → Full (strict)
2. Edge Certificates → Always Use HTTPS → On

### Opción B: Let's Encrypt Manual

```bash
# Instalar certbot con plugin DNS
sudo apt install certbot python3-certbot-dns-cloudflare

# Crear archivo de credenciales Cloudflare
nano ~/.secrets/cloudflare.ini
```

```ini
dns_cloudflare_email = tu@email.com
dns_cloudflare_api_key = tu_api_key_global
```

```bash
chmod 600 ~/.secrets/cloudflare.ini

# Obtener certificado wildcard
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials ~/.secrets/cloudflare.ini \
  -d notificct.dpdns.org \
  -d '*.notificct.dpdns.org'
```

---

## 🧪 Paso 6: Testing

### 1. Backend

```bash
# Healthcheck
curl https://tu-backend.com/api/health/

# Registro de empresa
curl -X POST https://tu-backend.com/api/public/registrar-empresa/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_empresa": "Test Clinic",
    "subdomain": "test-clinic",
    "nombre_admin": "Admin",
    "apellido_admin": "Test",
    "email_admin": "admin@test.com"
  }'
```

### 2. Frontend Público

```
https://notificct.dpdns.org
```

Verificar:
- Landing page carga correctamente
- Formulario de registro funciona
- Validación de subdominios en tiempo real
- Email de bienvenida se envía

### 3. Frontend de Aplicación

```
https://test-clinic.notificct.dpdns.org
```

Verificar:
- Login funciona
- Tenant se detecta correctamente
- Datos se filtran por empresa
- No hay data leaks entre tenants

---

## 📊 Paso 7: Monitoreo

### Sentry (Errores)

```bash
pip install sentry-sdk
```

```python
# settings.py
import sentry_sdk

if not DEBUG:
    sentry_sdk.init(
        dsn="https://tu-sentry-dsn",
        traces_sample_rate=0.1,
        environment="production",
    )
```

### Logs

```python
# settings.py - Ya configurado en tu proyecto
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/dental/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

---

## 🔄 Paso 8: CI/CD (Opcional)

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        run: curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}

  deploy-frontend-public:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        run: vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

---

## ✅ Checklist Final

### Backend
- [ ] Backend desplegado y accesible
- [ ] Variables de entorno configuradas
- [ ] Migraciones aplicadas
- [ ] Archivos estáticos servidos correctamente
- [ ] SSL configurado
- [ ] Emails funcionando
- [ ] S3 funcionando para archivos

### Frontend Público
- [ ] Landing page desplegada
- [ ] Formulario de registro funcional
- [ ] SSL configurado
- [ ] DNS apuntando correctamente

### Frontend de Aplicación
- [ ] Wildcard subdomain configurado
- [ ] Header X-Tenant-Subdomain enviándose
- [ ] Login funcional
- [ ] Multi-tenancy funcionando (data aislada)

### DNS & SSL
- [ ] Dominio base apuntando correctamente
- [ ] Wildcard subdomain configurado (`*`)
- [ ] Certificado SSL wildcard instalado
- [ ] HTTPS funcionando en todos los subdominios

### Testing
- [ ] Registro de empresa funciona end-to-end
- [ ] Email de bienvenida se envía
- [ ] Login en tenant específico funciona
- [ ] Datos están aislados entre tenants
- [ ] No hay CORS errors

---

## 🆘 Troubleshooting

### Error: "DisallowedHost"

**Solución:**
```python
# settings.py
ALLOWED_HOSTS = [
    '.notificct.dpdns.org',
    '*.notificct.dpdns.org',
]
```

### Error: CORS

**Solución:**
```python
# settings.py
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w-]+\.notificct\.dpdns\.org$",
]
```

### Error: Tenant no detectado

**Solución:**
Verificar que el frontend esté enviando el header:
```javascript
config.headers['X-Tenant-Subdomain'] = subdomain;
```

### Error: Certificado SSL wildcard no funciona

**Solución:**
Asegúrate de que:
1. El certificado cubra `*.notificct.dpdns.org`
2. El DNS no tenga proxy activado (nube gris en Cloudflare)
3. El servidor esté configurado para múltiples hostnames

---

## 📞 Soporte Post-Deployment

Después de desplegar, monitorea:
- Logs de aplicación
- Métricas de base de datos
- Uso de S3
- Tasa de emails enviados
- Errores en Sentry

---

¡Felicidades! Tu sistema SaaS multi-tenant está en producción 🎉
