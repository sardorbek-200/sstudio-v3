#!/usr/bin/env bash
set -e

echo "=== SStudio v3: Certbot To'liq Avtomatik SSL Sozlash ==="

# 1. Nginx configuratsiyalarini ulash
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
cp /root/app/v3/infra/nginx/*.conf /etc/nginx/sites-available/ 2>/dev/null || true

for f in /root/app/v3/infra/nginx/*.conf; do
    filename=$(basename "$f")
    ln -sf "/etc/nginx/sites-available/$filename" "/etc/nginx/sites-enabled/$filename"
done

# Eski eskirgan conf fayllarni tozalash
rm -f /etc/nginx/sites-enabled/*coming* /etc/nginx/sites-enabled/default 2>/dev/null || true

# Nginx holatini tekshirish va yangilash
nginx -t && systemctl reload nginx

# 2. DNS mavjudligini avtomatik tekshirish
ALL_DOMAINS="sstudio.uz www.sstudio.uz auth.sstudio.uz quizer.sstudio.uz shop.sstudio.uz admin.sstudio.uz"
VALID_DOMAINS=()

echo "--- DNS A recordlar tekshirilmoqda ---"
for d in $ALL_DOMAINS; do
    if getent ahostsv4 "$d" >/dev/null 2>&1 || host "$d" >/dev/null 2>&1 || ping -c 1 -W 1 "$d" >/dev/null 2>&1; then
        echo "  [OK] $d -> DNS faol, SSL olinadi"
        VALID_DOMAINS+=("-d" "$d")
    else
        echo "  [SKIP] $d -> DNS hali ulanmagan (NXDOMAIN xatosining oldi olindi)"
    fi
done

if [ ${#VALID_DOMAINS[@]} -eq 0 ]; then
    echo "Kamida asosiy domen qo'shilmoqda: sstudio.uz"
    VALID_DOMAINS=("-d" "sstudio.uz" "-d" "www.sstudio.uz")
fi

# 3. Certbot orqali klaviaturadan 1 yoki E bosishni talab qilmaydigan 100% avtomatik SSL
echo "Certbot ishga tushirilmoqda: ${VALID_DOMAINS[*]}"
certbot --nginx \
    "${VALID_DOMAINS[@]}" \
    --non-interactive \
    --agree-tos \
    --reinstall \
    --expand \
    --redirect \
    -m support@sstudio.uz

nginx -t && systemctl reload nginx

echo "=== SSL Sertifikati Hech Qanday Qo'lda Bosishsiz To'liq O'rnatildi! ==="
