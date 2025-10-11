# Guía Rápida de Despliegue - Sistema Multi-Tenant

## Tu Configuración Actual

- **Backend (EC2)**: http://notificct.dpdns.org
- **Frontend (Vercel)**: https://buy-dental-smile.vercel.app/
- **EC2 IP**: 18.220.214.178

## Endpoints Disponibles para tu Frontend

Tu frontend en Vercel debe usar estos endpoints:

### 1. Validar Subdominio
```
POST http://notificct.dpdns.org/api/public/validar-subdomain/

Body:
{
  "subdomain": "clinica-test"
}
```

### 2. Registrar Empresa SIN Pago (más simple para pruebas)
```
POST http://notificct.dpdns.org/api/public/registrar-empresa/

Body:
{
  "nombre_empresa": "Clínica Test",
  "subdomain": "test",
  "nombre_admin": "Juan",
  "apellido_admin": "Pérez",
  "email_admin": "juan@example.com",
  "telefono_admin": "+591 12345678",
  "sexo_admin": "Masculino"
}
```

### 3. Registrar Empresa CON Pago Stripe (para presentación completa)
```
POST http://notificct.dpdns.org/api/public/registrar-empresa-pago/

Body:
{
  "nombre_empresa": "Clínica Test",
  "subdomain": "test",
  "nombre_admin": "Juan",
  "apellido_admin": "Pérez",
  "email_admin": "juan@example.com",
  "telefono_admin": "+591 12345678",
  "sexo_admin": "Masculino",
  "payment_method_id": "pm_card_visa"
}
```

### 4. Crear Intención de Pago (si usas Stripe Elements)
```
POST http://notificct.dpdns.org/api/public/create-payment-intent/

Body:
{
  "amount": 9900
}
```

## Pasos para Desplegar en EC2

### Opción 1: Despliegue Manual (RECOMENDADO)

Copia y pega estos comandos en tu terminal conectado a EC2:

```bash
# 1. Conectar a EC2
ssh ubuntu@18.220.214.178

# 2. Una vez dentro, ejecuta todo esto:
cd /home/ubuntu/sitwo-project-backend && \
git pull origin master && \
source venv/bin/activate && \
pip install -r requirements.txt && \
python manage.py migrate --noinput && \
python manage.py collectstatic --noinput && \
sudo systemctl restart gunicorn && \
sudo systemctl restart nginx && \
echo "DESPLIEGUE COMPLETADO!"

# 3. Verificar que funciona
curl http://localhost:8000/api/health/

# 4. Ver logs si hay problemas
sudo journalctl -u gunicorn -n 50 --no-pager
```

### Opción 2: Usar el Script de Despliegue

```bash
# Desde tu EC2
cd /home/ubuntu/sitwo-project-backend
chmod +x deploy/update_server.sh
./deploy/update_server.sh
```

## Verificar que Todo Funciona

### Desde tu navegador:

1. **Health Check**:
   - http://notificct.dpdns.org/api/health/
   - Debe mostrar: `{"status":"ok"}`

2. **Probar endpoint de validación**:
   ```bash
   # Desde cualquier terminal (incluso tu Windows)
   curl -X POST http://notificct.dpdns.org/api/public/validar-subdomain/ \
     -H "Content-Type: application/json" \
     -d "{\"subdomain\": \"test123\"}"
   ```

3. **Probar registro de empresa**:
   ```bash
   curl -X POST http://notificct.dpdns.org/api/public/registrar-empresa/ \
     -H "Content-Type: application/json" \
     -d '{
       "nombre_empresa": "Clinica Demo",
       "subdomain": "demo",
       "nombre_admin": "Demo",
       "apellido_admin": "User",
       "email_admin": "demo@example.com"
     }'
   ```

## Configuración del Frontend (Vercel)

En tu proyecto de frontend en Vercel, asegúrate de tener estas variables de entorno:

```env
NEXT_PUBLIC_API_URL=http://notificct.dpdns.org/api
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_51SGSX5RxIhITCnEhwyPtoKa0LAWxHpMcr3Tw20Aqw9vkB8ncErHhIP1IvXmQjTdovbeQQMx55dGqiKqvTrJsjevj00Qd4GEebn
```

## Ejemplo de Llamada desde tu Frontend

```javascript
// Validar subdominio
const checkSubdomain = async (subdomain) => {
  const response = await fetch('http://notificct.dpdns.org/api/public/validar-subdomain/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ subdomain })
  });

  const data = await response.json();
  return data.disponible;
};

// Registrar empresa
const registerCompany = async (formData) => {
  const response = await fetch('http://notificct.dpdns.org/api/public/registrar-empresa/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      nombre_empresa: formData.companyName,
      subdomain: formData.subdomain,
      nombre_admin: formData.firstName,
      apellido_admin: formData.lastName,
      email_admin: formData.email,
      telefono_admin: formData.phone,
      sexo_admin: formData.gender
    })
  });

  const data = await response.json();

  if (data.ok) {
    console.log('Empresa creada:', data.empresa);
    console.log('URL de acceso:', data.url_acceso);
    console.log('Contraseña temporal:', data.password_temporal);
  }

  return data;
};
```

## Solución de Problemas Comunes

### Error: CORS

Si ves error de CORS desde tu frontend, verifica que el backend tiene configurado:

```python
# En settings.py
CORS_ALLOWED_ORIGINS = [
    "https://buy-dental-smile.vercel.app",
]
```

### Error 502 Bad Gateway

```bash
# Ver estado de servicios
sudo systemctl status gunicorn
sudo systemctl status nginx

# Reiniciar servicios
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

### Error de Variables de Entorno

```bash
# Verificar .env en el servidor
cat /home/ubuntu/sitwo-project-backend/.env

# Debe tener al menos:
# DEBUG=False
# DJANGO_SECRET_KEY=...
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_PUBLIC_KEY=pk_test_...
```

## Tarjetas de Prueba Stripe (para tu presentación)

Como estás usando Stripe TEST, usa estas tarjetas:

- **Visa exitosa**: 4242 4242 4242 4242
- **Visa con autenticación**: 4000 0025 0000 3155
- **Mastercard**: 5555 5555 5555 4444
- **American Express**: 3782 822463 10005
- **Rechazada**: 4000 0000 0000 0002

Cualquier:
- **Fecha de expiración**: Cualquier fecha futura (ej: 12/25)
- **CVC**: Cualquier 3 dígitos (ej: 123)
- **ZIP**: Cualquier código (ej: 12345)

## ¿Necesitas HTTPS?

**Para proyecto académico: NO es necesario**

- ✅ HTTP funciona perfectamente para demostración
- ✅ Stripe TEST acepta HTTP
- ✅ Stripe LIVE requeriría HTTPS (pero no lo necesitas)

Si quisieras HTTPS en el futuro (producción real):
1. Conseguir un certificado SSL (Let's Encrypt es gratis)
2. Configurar Nginx con SSL
3. Cambiar todas las URLs a https://

Pero para tu presentación actual, **HTTP es suficiente** ✅

## Resumen de URLs Importantes

- **API Base**: http://notificct.dpdns.org/api/
- **Health Check**: http://notificct.dpdns.org/api/health/
- **Registrar Empresa**: http://notificct.dpdns.org/api/public/registrar-empresa/
- **Validar Subdominio**: http://notificct.dpdns.org/api/public/validar-subdomain/
- **Frontend**: https://buy-dental-smile.vercel.app/

¡Listo para tu presentación! 🎉