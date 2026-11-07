#!/usr/bin/env bash
set -e

echo "=== SStudio v3: VPS Sozlash Boshlandi ==="

# 1. Kerakli papkalarni yaratish
mkdir -p /root/app/v3
cd /root/app/v3

# 2. Agar .env mavjud bo'lmasa, .env.example dan yaratamiz
if [ ! -f "/root/app/v3/.env" ]; then
    echo ".env fayli yaratilmoqda..."
    cp /root/app/v3/.env.example /root/app/v3/.env || true
fi

# 3. Virtual muhit (venv) tekshirish / yaratish
if [ ! -d "/root/app/v3/.venv" ]; then
    echo "Python venv yaratilmoqda..."
    python3 -m venv /root/app/v3/.venv
fi

# 4. Paketlarni o'rnatish
/root/app/v3/.venv/bin/pip install --upgrade pip
/root/app/v3/.venv/bin/pip install -r /root/app/v3/requirements.txt
/root/app/v3/.venv/bin/pip install email-validator

# 5. Systemd servislarni joylashtirish
echo "Systemd servislari ko'chirilmoqda..."
cp /root/app/v3/infra/systemd/*.service /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload

# 6. Servislarni yoqish
systemctl enable sstudio-auth sstudio-main || true
systemctl restart sstudio-auth sstudio-main || true

# 7. Nginx konfiguratsiyalarini ulash
echo "Nginx sozlanmoqda..."
cp /root/app/v3/infra/nginx/*.conf /etc/nginx/conf.d/ 2>/dev/null || true
nginx -t && systemctl reload nginx 2>/dev/null || true

echo "=== SStudio v3: Barcha xizmatlar muvaffaqiyatli ishga tushdi! ==="
