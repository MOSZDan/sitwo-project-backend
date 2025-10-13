#!/bin/bash

# Script para verificar que el error 502 esté solucionado

echo "========================================="
echo "VERIFICACIÓN DE SOLUCIÓN - ERROR 502"
echo "========================================="
echo ""

PASS=0
FAIL=0

# Función para verificar
check() {
    local test_name="$1"
    local command="$2"
    local expected="$3"

    echo -n "✓ $test_name... "
    result=$(eval "$command" 2>&1)

    if echo "$result" | grep -q "$expected"; then
        echo "✅ PASS"
        ((PASS++))
    else
        echo "❌ FAIL"
        echo "  Resultado: $result"
        ((FAIL++))
    fi
}

echo "=== PRUEBAS DE CONECTIVIDAD ==="
echo ""

# Test 1: Django en puerto 8000
check "Django responde en puerto 8000" \
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/health/" \
    "200"

# Test 2: Nginx en puerto 80 (localhost)
check "Nginx responde en puerto 80" \
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/" \
    "200"

# Test 3: Con header Host correcto
check "Nginx acepta Host: notificct.dpdns.org" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Host: notificct.dpdns.org' http://127.0.0.1/" \
    "200"

# Test 4: Health check con dominio
check "Health check funciona con dominio" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Host: notificct.dpdns.org' http://127.0.0.1/api/health/" \
    "200"

# Test 5: Verificar que no hay conflictos en Nginx
echo -n "✓ No hay conflictos en configuración de Nginx... "
nginx_test=$(sudo nginx -t 2>&1)
if echo "$nginx_test" | grep -q "conflicting"; then
    echo "❌ FAIL"
    echo "  Todavía hay configuraciones duplicadas"
    ((FAIL++))
else
    echo "✅ PASS"
    ((PASS++))
fi

# Test 6: Gunicorn está corriendo en puerto 8000
echo -n "✓ Gunicorn está corriendo en puerto 8000... "
if sudo ss -tlnp | grep -q ":8000"; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL"
    ((FAIL++))
fi

echo ""
echo "=== PRUEBAS DESDE INTERNET ==="
echo ""

# Test 7: Dominio público (requiere DNS)
echo -n "✓ Dominio público accesible (notificct.dpdns.org)... "
public_test=$(curl -s -o /dev/null -w '%{http_code}' http://notificct.dpdns.org/ --max-time 10 2>&1)
if [ "$public_test" = "200" ]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (HTTP $public_test)"
    if [ "$public_test" = "502" ]; then
        echo "  ⚠️  Todavía obtienes 502 Bad Gateway"
        echo "  Verifica que la configuración de Nginx esté actualizada"
    fi
    ((FAIL++))
fi

# Test 8: Health check desde internet
echo -n "✓ Health check accesible desde internet... "
health_test=$(curl -s -o /dev/null -w '%{http_code}' http://notificct.dpdns.org/api/health/ --max-time 10 2>&1)
if [ "$health_test" = "200" ]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (HTTP $health_test)"
    ((FAIL++))
fi

echo ""
echo "=== INFORMACIÓN ADICIONAL ==="
echo ""

# Mostrar configuración activa de Nginx
echo "Archivos de configuración activos en Nginx:"
ls -la /etc/nginx/sites-enabled/
echo ""

# Mostrar upstream configurado
echo "Upstream configurado en Nginx:"
grep -A 2 "upstream dental_clinic" /etc/nginx/sites-enabled/* 2>/dev/null || echo "No encontrado"
echo ""

# Mostrar procesos de Gunicorn
echo "Procesos de Gunicorn corriendo:"
ps aux | grep gunicorn | grep -v grep | head -5
echo ""

# Mostrar últimas líneas del log de error de Nginx
echo "Últimas 5 líneas del log de error de Nginx:"
sudo tail -5 /var/log/nginx/dental_clinic_error.log 2>/dev/null || echo "Sin errores recientes"
echo ""

echo "========================================="
echo "RESUMEN"
echo "========================================="
echo "Pruebas pasadas: $PASS"
echo "Pruebas falladas: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 ¡ÉXITO! Todo está funcionando correctamente"
    echo ""
    echo "Tu sitio está accesible en:"
    echo "  🌐 http://notificct.dpdns.org"
    echo ""
    echo "Próximos pasos recomendados:"
    echo "  1. Configurar HTTPS con Let's Encrypt (certbot)"
    echo "  2. Configurar Gunicorn como servicio systemd permanente"
    echo "  3. Configurar logs rotativos"
else
    echo "⚠️  Hay $FAIL problema(s) que necesitan atención"
    echo ""
    if [ "$public_test" = "502" ]; then
        echo "PROBLEMA PRINCIPAL: Todavía obtienes 502 Bad Gateway"
        echo ""
        echo "Posibles causas:"
        echo "  1. La configuración de Nginx no se actualizó correctamente"
        echo "  2. Nginx no se recargó después de los cambios"
        echo "  3. Todavía hay configuraciones duplicadas"
        echo ""
        echo "Solución:"
        echo "  sudo rm /etc/nginx/sites-enabled/dental_clinic_backend"
        echo "  sudo nano /etc/nginx/sites-available/dental_clinic"
        echo "  # Cambiar 'server unix:...' por 'server 127.0.0.1:8000'"
        echo "  sudo nginx -t"
        echo "  sudo systemctl reload nginx"
    fi
fi

echo ""
echo "========================================="