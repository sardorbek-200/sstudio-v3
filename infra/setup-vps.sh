#!/usr/bin/env bash
set -e

echo "=== SStudio v3: VPS Sozlash Boshlandi ==="

# 1. Kerakli papkalarni yaratish
mkdir -p /root/app/v3
cd /root/app/v3

# 2. Virtual muhit (venv) tekshirish / yaratish
if [ ! -d "/root/app/v3/.venv" ]; then
    echo "Python venv yaratilmoqda..."
    python3 -m venv /root/app/v3/.venv
fi

# 3. Paketlarni o'rnatish
/root/app/v3/.venv/bin/pip install --upgrade pip
/root/app/v3/.venv/bin/pip install -r /root/app/v3/requirements.txt
/root/app/v3/.venv/bin/pip install email-validator

# 4. Systemd servislarni joylashtirish
echo "Systemd servislari ko'chirilmoqda..."
cp /root/app/v3/infra/systemd/*.service /etc/systemd/system/
systemctl daemon-reload

# 5. Servislarni yoqish
systemctl enable sstudio-auth
systemctl restart sstudio-auth

# 6. Nginx konfiguratsiyalarini ulash
echo "Nginx sozlanmoqda..."
cp /root/app/v3/infra/nginx/*.conf /etc/nginx/conf.d/
nginx -t && systemctl reload nginx

echo "=== SStudio v3: Barcha xizmatlar muvaffaqiyatli ishga tushdi! ==="
