#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🚨 SStudio v3: Serverni To'liq Tozalash va Qayta Sozlash"
echo "   (PM2 va Davomatchi to'xtatiladi, SStudio v3 ko'tariladi)"
echo "=========================================================="

# 1. PM2 ni to'liq to'xtatish
echo "[1/7] PM2 jarayonlari to'xtatilmoqda..."
if command -v pm2 >/dev/null 2>&1; then
    pm2 stop all || true
    pm2 delete all || true
    pm2 kill || true
fi
systemctl stop pm2-root 2>/dev/null || true
systemctl disable pm2-root 2>/dev/null || true

# 2. Davomatchi servislari va jarayonlarini to'xtatish (fayllari saqlanadi)
echo "[2/7] Davomatchi jarayonlari to'xtatilmoqda (fayllariga tegilmaydi)..."
pkill -9 -f davomatchi || true
pkill -9 -f /root/app/davomatchi || true
systemctl stop davomatchi* 2>/dev/null || true
systemctl disable davomatchi* 2>/dev/null || true

# 3. SStudio portlarini (8000..8005) tozalash
echo "[3/7] SStudio portlari (8000, 8001, 8002, 8003, 8004, 8005) tozalanmoqda..."
if command -v fuser >/dev/null 2>&1; then
    fuser -k 8000/tcp 8001/tcp 8002/tcp 8003/tcp 8004/tcp 8005/tcp 2>/dev/null || true
fi

# 4. PostgreSQL Alembic Migratsiyasini to'liq yurgizish
echo "[4/7] PostgreSQL sxemalari va jadvallari (Alembic) yangilanmoqda..."
cd /root/app/v3
if [ -f "/root/app/v3/.venv/bin/alembic" ]; then
    /root/app/v3/.venv/bin/alembic upgrade head || echo "⚠️ Alembic xabari (davom etilmoqda)..."
fi

# 5. Nginx konfiguratsiyalarini tozalash va faqat SStudio v3 ni ulash
echo "[5/7] Nginx to'liq qayta sozlanmoqda (Eski conf fayllar tozalanmoqda)..."
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

# 6. SStudio v3 Systemd servislarni yangilash va ishga tushirish
echo "[6/7] SStudio v3 servislari (Main, Auth, Quizer, Shop, SAgent, Admin) ishga tushirilmoqda..."
cp /root/app/v3/infra/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable sstudio-main sstudio-auth sstudio-quizer sstudio-shop sstudio-sagent sstudio-admin 2>/dev/null || true
systemctl restart sstudio-main sstudio-auth sstudio-quizer sstudio-shop sstudio-sagent sstudio-admin

# 7. Nginx tekshirish va qayta ishga tushirish
echo "[7/7] Nginx qayta ishga tushirilmoqda..."
nginx -t
systemctl restart nginx

echo ""
echo "=========================================================="
echo "✅ HAMMASI MUVAFFAQIYATLI YAKUNLANDI!"
echo "   SStudio v3 to'liq ishga tushdi:"
echo "   - sstudio.uz          -> 8000"
echo "   - auth.sstudio.uz     -> 8001"
echo "   - quizer.sstudio.uz   -> 8002"
echo "   - shop.sstudio.uz     -> 8003"
echo "   - sagent.sstudio.uz   -> 8004"
echo "   - admin.sstudio.uz    -> 8005"
echo "=========================================================="
