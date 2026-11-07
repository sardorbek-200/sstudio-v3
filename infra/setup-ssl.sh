#!/usr/bin/env bash
set -e

echo "=== SStudio v3: Certbot SSL Sozlash Boshlandi ==="

# 1. Certbot va Nginx modulini o'rnatish
echo "Certbot o'rnatilmoqda..."
apt-get update -y
apt-get install -y certbot python3-certbot-nginx

# 2. Nginx ishlayotganini tekshirish
systemctl reload nginx || systemctl restart nginx

# 3. SSL sertifikatini olish va Nginx ga ulash
# Diqqat: DNS (A yozuvlar) server IP ga yo'naltirilgan bo'lishi shart!
echo "SSL sertifikati olinmoqda..."
certbot --nginx \
    -d sstudio.uz \
    -d www.sstudio.uz \
    -d auth.sstudio.uz \
    -d quizer.sstudio.uz \
    --non-interactive \
    --agree-tos \
    -m support@sstudio.uz \
    --redirect

# 4. Avtomatik yangilanishni sinash
certbot renew --dry-run

echo "=== SSL Muvaffaqiyatli O'rnatildi! Barcha domenlar HTTPS da ishlamoqda! ==="
