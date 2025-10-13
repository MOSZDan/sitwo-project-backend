#!/bin/bash

################################################################################
# SCRIPT PARA CONFIGURAR ROUTE 53 (AWS DNS)
################################################################################
# Este script automatiza la configuración de Route 53 para tu dominio
################################################################################

set -e

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

print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

################################################################################
# CONFIGURACIÓN
################################################################################

print_section "CONFIGURACIÓN DE ROUTE 53"

# Pedir información al usuario
read -p "Ingresa tu dominio (ej: notificct.dpdns.org): " DOMAIN_NAME
read -p "Ingresa la IP pública de tu EC2: " EC2_IP

if [ -z "$DOMAIN_NAME" ] || [ -z "$EC2_IP" ]; then
    print_error "Dominio e IP son requeridos"
    exit 1
fi

print_message "Dominio: $DOMAIN_NAME"
print_message "IP EC2: $EC2_IP"

################################################################################
# INSTALAR AWS CLI SI NO ESTÁ INSTALADO
################################################################################

print_section "VERIFICANDO AWS CLI"

if ! command -v aws &> /dev/null; then
    print_message "Instalando AWS CLI..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
    print_message "✓ AWS CLI instalado"
else
    print_message "✓ AWS CLI ya está instalado"
fi

################################################################################
# CONFIGURAR CREDENCIALES DE AWS
################################################################################

print_section "CONFIGURANDO CREDENCIALES AWS"

# Verificar si ya hay credenciales configuradas
if [ ! -f ~/.aws/credentials ]; then
    print_message "Configurando credenciales de AWS..."
    read -p "AWS Access Key ID: " AWS_ACCESS_KEY
    read -sp "AWS Secret Access Key: " AWS_SECRET_KEY
    echo ""

    aws configure set aws_access_key_id "$AWS_ACCESS_KEY"
    aws configure set aws_secret_access_key "$AWS_SECRET_KEY"
    aws configure set default.region us-east-2
    aws configure set default.output json

    print_message "✓ Credenciales configuradas"
else
    print_message "✓ Credenciales ya configuradas"
fi

################################################################################
# OBTENER O CREAR HOSTED ZONE
################################################################################

print_section "CONFIGURANDO HOSTED ZONE EN ROUTE 53"

# Buscar hosted zone existente
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name --query "HostedZones[?Name=='${DOMAIN_NAME}.'].Id" --output text | cut -d'/' -f3)

if [ -z "$HOSTED_ZONE_ID" ]; then
    print_message "Creando nueva hosted zone para $DOMAIN_NAME..."

    # Crear hosted zone
    CALLER_REFERENCE=$(date +%s)
    CREATE_OUTPUT=$(aws route53 create-hosted-zone \
        --name "$DOMAIN_NAME" \
        --caller-reference "$CALLER_REFERENCE" \
        --hosted-zone-config Comment="Hosted zone para sistema dental multi-tenant")

    HOSTED_ZONE_ID=$(echo "$CREATE_OUTPUT" | jq -r '.HostedZone.Id' | cut -d'/' -f3)

    print_message "✓ Hosted zone creada: $HOSTED_ZONE_ID"

    # Mostrar nameservers
    print_message "IMPORTANTE: Configura estos nameservers en tu proveedor de dominio:"
    aws route53 get-hosted-zone --id "$HOSTED_ZONE_ID" | jq -r '.DelegationSet.NameServers[]'
else
    print_message "✓ Usando hosted zone existente: $HOSTED_ZONE_ID"
fi

################################################################################
# CREAR REGISTROS DNS
################################################################################

print_section "CREANDO REGISTROS DNS"

# Crear archivo de configuración para los registros
cat > /tmp/route53-changes.json <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$DOMAIN_NAME",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [
          {
            "Value": "$EC2_IP"
          }
        ]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "*.$DOMAIN_NAME",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [
          {
            "Value": "$EC2_IP"
          }
        ]
      }
    }
  ]
}
EOF

print_message "Aplicando cambios en Route 53..."

# Aplicar cambios
CHANGE_ID=$(aws route53 change-resource-record-sets \
    --hosted-zone-id "$HOSTED_ZONE_ID" \
    --change-batch file:///tmp/route53-changes.json \
    --query 'ChangeInfo.Id' \
    --output text)

print_message "✓ Cambios enviados: $CHANGE_ID"

# Esperar a que los cambios se propaguen
print_message "Esperando propagación de DNS (esto puede tomar unos segundos)..."
aws route53 wait resource-record-sets-changed --id "$CHANGE_ID"

print_message "✓ Cambios propagados exitosamente"

# Limpiar archivo temporal
rm -f /tmp/route53-changes.json

################################################################################
# VERIFICAR CONFIGURACIÓN
################################################################################

print_section "VERIFICANDO CONFIGURACIÓN DNS"

print_message "Esperando 10 segundos para verificación..."
sleep 10

print_message "Verificando resolución DNS..."
echo ""
nslookup "$DOMAIN_NAME" || print_error "No se pudo resolver $DOMAIN_NAME"
echo ""

################################################################################
# RESUMEN FINAL
################################################################################

print_section "✅ CONFIGURACIÓN DE ROUTE 53 COMPLETADA"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Route 53 configurado exitosamente${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo "📍 Registros DNS creados:"
echo "   - $DOMAIN_NAME → $EC2_IP"
echo "   - *.$DOMAIN_NAME → $EC2_IP (wildcard para subdominios)"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Espera a que el DNS se propague completamente (puede tomar hasta 48 horas)"
echo "   2. Verifica la propagación: https://dnschecker.org"
echo "   3. Configura SSL con certbot en tu servidor EC2:"
echo "      sudo certbot --nginx -d $DOMAIN_NAME -d *.$DOMAIN_NAME"
echo "   4. Actualiza las variables de entorno en Vercel:"
echo "      VITE_API_URL=https://$DOMAIN_NAME/api"
echo "      VITE_BASE_DOMAIN=$DOMAIN_NAME"
echo ""
echo "🔍 Comandos útiles:"
echo "   - Ver hosted zones: aws route53 list-hosted-zones"
echo "   - Ver registros: aws route53 list-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID"
echo "   - Verificar DNS: nslookup $DOMAIN_NAME"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

################################################################################
# FIN DEL SCRIPT
################################################################################