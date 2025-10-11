# 🚀 Despliegue Rápido - 5 Minutos

## ⚠️ URGENTE: Seguridad

**REVOCA INMEDIATAMENTE** las credenciales AWS que compartiste:
- Ve a: [AWS IAM Console](https://console.aws.amazon.com/iam/)
- Security Credentials → Access Keys
- **Desactiva/Elimina:** `AKIAYF2ZN5QSXKCBL3WB`

---

## 📋 Pasos Rápidos

### 1️⃣ Conectar a EC2

```bash
ssh -i "tu-llave.pem" ubuntu@18.220.214.178
```

### 2️⃣ Descargar y ejecutar

```bash
# Clonar repositorio
cd /home/ubuntu
git clone <tu-repo-url> sitwo-project-backend
cd sitwo-project-backend

# Crear archivo .env
nano .env
# Pega la configuración (ver abajo)

# Ejecutar script de despliegue
chmod +x deploy_to_aws.sh
./deploy_to_aws.sh
```

### 3️⃣ Configuración mínima .env

```bash
DEBUG=False
DJANGO_SECRET_KEY=genera-una-clave-segura-aqui
DB_NAME=tu_db
DB_USER=tu_user
DB_PASSWORD=tu_pass
DB_HOST=tu-host.supabase.co
DB_PORT=5432
AWS_ACCESS_KEY_ID=NUEVAS_CREDENCIALES
AWS_SECRET_ACCESS_KEY=NUEVAS_CREDENCIALES
AWS_STORAGE_BUCKET_NAME=tu-bucket
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_PRICE_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 4️⃣ Actualizar Vercel

En [vercel.com](https://vercel.com) → tu proyecto → Settings → Environment Variables:

```
VITE_API_URL=https://notificct.dpdns.org/api
VITE_BASE_DOMAIN=notificct.dpdns.org
VITE_STRIPE_PUBLIC_KEY=pk_test_...
```

### 5️⃣ Verificar

```bash
curl https://notificct.dpdns.org/api/health/
```

---

## 🔧 Comandos Útiles

```bash
# Ver logs
sudo tail -f /var/log/gunicorn/gunicorn.err.log

# Reiniciar servicios
sudo supervisorctl restart gunicorn
sudo systemctl restart nginx

# Estado
sudo supervisorctl status
```

---

## 📚 Documentación Completa

Ver: `GUIA_DESPLIEGUE_AWS.md`

---

## 🆘 Problema Resuelto

**Error:** "No se pudo verificar la disponibilidad"

**Causa:** Variables de entorno incorrectas en Vercel

**Solución:** Actualizar `VITE_API_URL` en Vercel como se indica arriba ☝️