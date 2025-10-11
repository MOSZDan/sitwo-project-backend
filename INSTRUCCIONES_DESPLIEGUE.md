# Instrucciones para Desplegar Cambios en EC2

## Paso 1: Conectarse al servidor EC2

Abre tu terminal/PowerShell y ejecuta:

```bash
ssh ubuntu@18.220.214.178
```

## Paso 2: Actualizar el código

Una vez dentro del servidor, ejecuta estos comandos:

```bash
cd /home/ubuntu/sitwo-project-backend

# Obtener últimos cambios
git pull origin master

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias (por si hay nuevas)
pip install -r requirements.txt

# Ejecutar migraciones
python manage.py migrate --noinput

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Reiniciar servicios
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## Paso 3: Verificar que funciona

```bash
# Ver estado de los servicios
sudo systemctl status gunicorn --no-pager | head -10
sudo systemctl status nginx --no-pager | head -10

# Probar el health check
curl http://localhost:8000/api/health/
```

## Paso 4: Probar desde el navegador

1. Abre tu navegador
2. Ve a: http://notificct.dpdns.org/api/health/
3. Deberías ver: `{"status": "ok"}`

## Paso 5: Probar el registro desde Vercel

1. Ve a tu frontend: https://buy-dental-smile.vercel.app/
2. Intenta registrar una nueva empresa con un subdominio
3. El endpoint que debe funcionar es: `http://notificct.dpdns.org/api/saas/registrar-empresa-con-pago/`

## Verificar Variables de Entorno en el Servidor

Si algo falla, verifica que el archivo `.env` en el servidor tenga las variables correctas:

```bash
cat /home/ubuntu/sitwo-project-backend/.env
```

Debe contener al menos:

```env
DEBUG=False
DJANGO_SECRET_KEY=tu-secret-key-segura

# Base de datos
DB_NAME=tu_db
DB_USER=tu_user
DB_PASSWORD=tu_password
DB_HOST=tu_host.supabase.co
DB_PORT=5432

# Stripe (modo TEST para tu presentación)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_PRICE_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS (si usas S3)
AWS_ACCESS_KEY_ID=tu_aws_access_key_id
AWS_SECRET_ACCESS_KEY=tu_aws_secret_key
AWS_STORAGE_BUCKET_NAME=dental-clinic-files
```

## Solución de Problemas

### Si gunicorn falla:

```bash
# Ver logs de gunicorn
sudo journalctl -u gunicorn -n 50 --no-pager

# Ver logs de nginx
sudo tail -f /var/log/nginx/error.log
```

### Si hay error de migraciones:

```bash
python manage.py migrate --fake-initial
```

### Si hay error de permisos:

```bash
sudo chown -R ubuntu:ubuntu /home/ubuntu/sitwo-project-backend
```

## Probar Endpoint de Registro

Desde tu computadora local, prueba el endpoint:

```bash
curl -X POST http://notificct.dpdns.org/api/saas/registrar-empresa-con-pago/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Clinica Test",
    "subdomain": "test",
    "email": "test@example.com",
    "payment_method_id": "pm_card_visa"
  }'
```

## Endpoints Disponibles

Una vez desplegado, estos endpoints deben funcionar desde tu frontend en Vercel:

- ✅ `GET /api/health/` - Health check
- ✅ `POST /api/saas/registrar-empresa-con-pago/` - Registrar empresa
- ✅ `POST /api/stripe/create-payment-intent/` - Crear intención de pago
- ✅ `POST /api/stripe/webhook/` - Webhook de Stripe

## Nota Importante

Como estás usando Stripe en modo TEST, no se procesarán pagos reales. Usa estas tarjetas de prueba:

- Visa: `4242 4242 4242 4242`
- Mastercard: `5555 5555 5555 4444`
- Expiry: Cualquier fecha futura
- CVC: Cualquier 3 dígitos
- ZIP: Cualquier código

---

¡Listo! Una vez que hagas el despliegue, tu frontend en Vercel podrá comunicarse con el backend y registrar empresas con subdominios.