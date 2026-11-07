#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🚨 SStudio v3: Serverni To'liq Tozalash va Qayta Sozlash"
echo "   (PM2 va Davomatchi butunlay yo'q qilinadi!)"
echo "=========================================================="

# 1. PM2 ni to'liq to'xtatish va o'chirish
echo "[1/6] PM2 jarayonlari butunlay to'xtatilmoqda..."
if command -v pm2 >/dev/null 2>&1; then
    pm2 stop all || true
    pm2 delete all || true
    pm2 kill || true
fi
systemctl stop pm2-root 2>/dev/null || true
systemctl disable pm2-root 2>/dev/null || true
rm -rf /root/.pm2

# 2. Davomatchi servislari va jarayonlarini to'liq o'ldirish
echo "[2/6] Davomatchi jarayonlari o'ldirilmoqda..."
pkill -9 -f davomatchi || true
pkill -9 -f /root/app/davomatchi || true
systemctl stop davomatchi* 2>/dev/null || true
systemctl disable davomatchi* 2>/dev/null || true
rm -f /etc/systemd/system/davomatchi* 2>/dev/null || true

# 3. 8000, 8001, 8002, 8006, 8007 portlarini bo'shatish
echo "[3/6] SStudio portlari (8000, 8001, 8002, 8006, 8007) tozalanmoqda..."
if command -v fuser >/dev/null 2>&1; then
    fuser -k 8000/tcp 8001/tcp 8002/tcp 8006/tcp 8007/tcp 2>/dev/null || true
fi

# 4. Nginx konfiguratsiyalarini to'liq tozalash va faqat SStudio v3 ni ulash
echo "[4/6] Nginx to'liq qayta sozlanmoqda (Eski conf fayllar tozalanmoqda)..."
rm -f /etc/nginx/sites-enabled/*davomatchi* /etc/nginx/sites-available/*davomatchi* 2>/dev/null || true
rm -f /etc/nginx/conf.d/*davomatchi* 2>/dev/null || true
rm -f /etc/nginx/sites-enabled/*coming* /etc/nginx/sites-enabled/default 2>/dev/null || true
rm -f /etc/nginx/conf.d/*.conf 2>/dev/null || true

mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
cp /root/app/v3/infra/nginx/*.conf /etc/nginx/sites-available/

for f in /root/app/v3/infra/nginx/*.conf; do
    filename=$(basename "$f")
    ln -sf "/etc/nginx/sites-available/$filename" "/etc/nginx/sites-enabled/$filename"
done

# 5. SStudio v3 systemd servislarni yangilash va ishga tushirish
echo "[5/6] SStudio v3 servislari (Main, Auth, Quizer, Shop, Admin) qayta ishga tushirilmoqda..."
cp /root/app/v3/infra/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable sstudio-main sstudio-auth sstudio-quizer sstudio-shop sstudio-admin 2>/dev/null || true
systemctl restart sstudio-main sstudio-auth sstudio-quizer sstudio-shop sstudio-admin

# 6. Nginx tekshirish va restart
echo "[6/6] Nginx qayta ishga tushirilmoqda..."
nginx -t
systemctl restart nginx

echo "=========================================================="
echo "✅ TIZIM TO'LIQ TOZALANDI!"
echo "   PM2 yo'q qilindi."
echo "   Davomatchi yo'q qilindi."
echo "   Nginx faqat SStudio v3 uchun sozlandi."
echo "=========================================================="
