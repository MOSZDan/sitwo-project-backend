# 🌐 Configuración de Subdominios Automáticos

Esta guía te ayudará a configurar subdominios automáticos para tu sistema multi-tenant usando AWS y Cloudflare.

---

## 📋 Resumen

Tu sistema funciona con subdominios dinámicos:
- **Sitio público**: `https://notificct.dpdns.org` (landing page donde se registran empresas)
- **Empresas**: `https://[subdominio].notificct.dpdns.org` (cada empresa tiene su propio subdominio)

Ejemplo:
- Empresa "Norte" → `https://norte.notificct.dpdns.org`
- Empresa "Sur" → `https://sur.notificct.dpdns.org`

---

## 🎯 Arquitectura

```
Usuario → Cloudflare (DNS + CDN) → AWS (Backend) → Base de Datos
```

**Cloudflare**: Maneja el DNS con wildcard (`*.notificct.dpdns.org`)
**AWS**: Aloja tu backend Django que identifica la empresa por el subdominio

---

## ⚙️ Configuración Paso a Paso

### 1️⃣ Configurar Cloudflare DNS

#### Opción A: Tu dominio ya está en Cloudflare

1. Ve a tu panel de Cloudflare
2. Selecciona tu dominio `dpdns.org`
3. Ve a **DNS** → **Records**
4. Agrega estos registros:

**Registro para el dominio base:**
```
Type: A
Name: notificct
Content: [IP_DE_TU_SERVIDOR_AWS]
Proxy status: Proxied (naranja)
TTL: Auto
```

**Registro wildcard para todos los subdominios:**
```
Type: A
Name: *.notificct
Content: [IP_DE_TU_SERVIDOR_AWS]
Proxy status: Proxied (naranja)
TTL: Auto
```

#### Opción B: Usar CNAME si tienes Load Balancer

Si usas un Load Balancer de AWS en lugar de IP directa:

```
Type: CNAME
Name: notificct
Content: tu-load-balancer.us-east-2.elb.amazonaws.com
Proxy status: Proxied (naranja)

Type: CNAME
Name: *.notificct
Content: tu-load-balancer.us-east-2.elb.amazonaws.com
Proxy status: Proxied (naranja)
```

---

### 2️⃣ Configurar SSL en Cloudflare

1. Ve a **SSL/TLS** → **Overview**
2. Selecciona **Full (strict)**
3. Ve a **Edge Certificates**
4. Activa:
   - ✅ Always Use HTTPS
   - ✅ Automatic HTTPS Rewrites
   - ✅ Universal SSL (debe estar activo por defecto)

El certificado wildcard se genera automáticamente y cubre:
- `notificct.dpdns.org`
- `*.notificct.dpdns.org`

---

### 3️⃣ Configurar tu Backend en AWS

#### Si usas EC2 directamente:

Tu backend Django ya está configurado para detectar subdominios. Solo asegúrate de:

1. **Verificar que Nginx está configurado correctamente:**

```bash
sudo nano /etc/nginx/sites-available/dental
```

El archivo debe tener:
```nginx
server {
    listen 80;
    server_name notificct.dpdns.org *.notificct.dpdns.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

2. **Instalar certificado SSL en el servidor:**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d notificct.dpdns.org -d '*.notificct.dpdns.org'
```

**IMPORTANTE**: Para certificado wildcard, necesitas validación DNS. Certbot te pedirá agregar un registro TXT en Cloudflare temporalmente.

#### Si usas Load Balancer de AWS:

1. Ve a **EC2 → Load Balancers**
2. Selecciona tu load balancer
3. Agrega listener HTTPS (puerto 443)
4. Solicita certificado SSL desde **AWS Certificate Manager (ACM)**:
   - Dominio: `notificct.dpdns.org`
   - Dominio adicional: `*.notificct.dpdns.org`
5. AWS te dará registros CNAME para validar en Cloudflare

---

## 🧪 Probar la Configuración

### 1. Verificar DNS

```bash
# Probar dominio base
nslookup notificct.dpdns.org

# Probar subdominio cualquiera
nslookup prueba.notificct.dpdns.org
```

Ambos deben resolver a la misma IP de tu servidor AWS.

### 2. Probar Backend

```bash
# Probar que el backend responde
curl https://notificct.dpdns.org/api/health/

# Probar endpoint público de registro
curl -X POST https://notificct.dpdns.org/api/public/registrar-empresa/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_empresa": "Clínica Test",
    "subdomain": "test",
    "nombre_admin": "Admin",
    "apellido_admin": "Test",
    "email_admin": "admin@test.com"
  }'
```

### 3. Probar Subdominio Creado

Después de registrar una empresa con subdominio "test":

```bash
# El middleware debe detectar el tenant
curl -H "X-Tenant-Subdomain: test" https://notificct.dpdns.org/api/pacientes/

# O directamente desde el subdominio
curl https://test.notificct.dpdns.org/api/pacientes/
```

---

## 🔧 Cómo Funciona Internamente

### Backend (Django)

Tu `api/middleware.py` ya tiene el middleware que detecta el subdominio:

```python
class TenantMiddleware:
    def __call__(self, request):
        # Extrae el subdominio del host
        host = request.get_host()

        # Extrae "norte" de "norte.notificct.dpdns.org"
        subdomain = host.split('.')[0]

        # Busca la empresa en la base de datos
        empresa = Empresa.objects.get(subdomain=subdomain, activo=True)

        # Guarda la empresa en request para usarla en las vistas
        request.tenant = empresa
```

### Frontend

Tu frontend debe enviar el header `X-Tenant-Subdomain` en cada petición:

```javascript
// src/utils/tenant.js
export function getTenantFromURL() {
  const host = window.location.host;
  const parts = host.split('.');

  // Extrae "norte" de "norte.notificct.dpdns.org"
  return parts[0];
}

// src/api/client.js
api.interceptors.request.use((config) => {
  const subdomain = getTenantFromURL();
  config.headers['X-Tenant-Subdomain'] = subdomain;
  return config;
});
```

---

## 📝 Checklist de Configuración

### Cloudflare
- [ ] Dominio agregado a Cloudflare
- [ ] Registro A/CNAME para `notificct` creado
- [ ] Registro A/CNAME wildcard `*.notificct` creado
- [ ] SSL configurado en modo "Full (strict)"
- [ ] Universal SSL activo

### AWS Backend
- [ ] Servidor/Load Balancer configurado
- [ ] Nginx acepta `*.notificct.dpdns.org`
- [ ] Certificado SSL instalado (wildcard)
- [ ] Backend responde en puerto 80/443
- [ ] Security Groups permiten tráfico HTTP/HTTPS

### Django Settings
- [ ] `ALLOWED_HOSTS` incluye `.notificct.dpdns.org`
- [ ] `CORS_ALLOWED_ORIGIN_REGEXES` configurado para subdominios
- [ ] `CSRF_TRUSTED_ORIGINS` incluye subdominios
- [ ] Middleware `TenantMiddleware` activo

### Base de Datos
- [ ] Tabla `Empresa` tiene campo `subdomain` único
- [ ] Al menos una empresa creada con subdominio válido

---

## 🆘 Problemas Comunes

### Error: "Empresa no encontrada" o 404

**Causa**: El subdominio no existe en la base de datos.

**Solución**:
```bash
python manage.py shell
```
```python
from api.models import Empresa
empresas = Empresa.objects.all()
for e in empresas:
    print(f"{e.nombre} -> {e.subdomain}")
```

Verifica que el subdominio existe y está activo.

### Error: "DisallowedHost at /"

**Causa**: Django no reconoce el dominio.

**Solución**: Verifica `settings.py`:
```python
ALLOWED_HOSTS = [
    ".notificct.dpdns.org",
    "*.notificct.dpdns.org",
    "localhost",
]
```

### Error: CORS o CSRF

**Causa**: El frontend no puede hacer peticiones al backend.

**Solución**: Verifica `settings.py`:
```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w-]+\.notificct\.dpdns\.org$",
]

CSRF_TRUSTED_ORIGINS = [
    "https://*.notificct.dpdns.org",
]
```

### El certificado SSL no cubre subdominios

**Causa**: Certificado no es wildcard.

**Solución**: Regenera el certificado con:
```bash
sudo certbot certonly --manual --preferred-challenges dns \
  -d notificct.dpdns.org -d '*.notificct.dpdns.org'
```

---

## ✅ Verificación Final

Una vez configurado todo, deberías poder:

1. ✅ Acceder a `https://notificct.dpdns.org` (landing page)
2. ✅ Registrar una empresa nueva con subdominio "demo"
3. ✅ Acceder a `https://demo.notificct.dpdns.org` (app de la empresa)
4. ✅ Hacer login en la app de la empresa
5. ✅ Ver solo los datos de esa empresa

---

¡Listo! Con esta configuración, cada nueva empresa registrada automáticamente tendrá su propio subdominio funcionando sin necesidad de configuración manual.