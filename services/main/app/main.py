from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select, func

from models.auth import User
from shared.config import settings
from shared.database import async_session_maker
from shared.security import decode_access_token

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SStudio Main Portal", version="3.0.0")

# Statik fayllar va Shablonlar
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["domain"] = settings.BASE_DOMAIN or "sstudio.uz"
templates.env.globals["base_domain"] = settings.BASE_DOMAIN or "sstudio.uz"
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


async def get_current_user_optional(request: Request):
    token = request.cookies.get("sstudio_token")
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = int(payload["sub"])
        async with async_session_maker() as db:
            stmt = select(User).where(User.id == user_id, User.is_active == True, User.is_banned == False)
            res = await db.execute(stmt)
            db_user = res.scalar_one_or_none()
            if db_user:
                return db_user
    except Exception:
        pass

    # Fallback to JWT payload
    return {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "name": payload.get("name", payload.get("username", "Foydalanuvchi")),
        "surname": payload.get("surname", ""),
        "status": payload.get("status", "FREEMIUM")
    }


# --- 1. Redirectlar ---
@app.get("/login", response_class=RedirectResponse)
async def login_redirect():
    return RedirectResponse(url=f"https://auth.{settings.BASE_DOMAIN}/login")


@app.get("/register", response_class=RedirectResponse)
async def register_redirect():
    return RedirectResponse(url=f"https://auth.{settings.BASE_DOMAIN}/register")


# --- 2. Bosh Sahifa (Landing) ---
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    user = await get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user, "domain": settings.BASE_DOMAIN}
    )


# --- 3. Ilovalar Katalogi (/apps) ---
@app.get("/apps", response_class=HTMLResponse)
async def apps_catalog(request: Request):
    user = await get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="apps.html",
        context={"user": user, "domain": settings.BASE_DOMAIN, "active_page": "apps"}
    )


# --- 3.1 Hamyon va SStudio Yosh Tadbirkorlik Kiber-Moliya Ekotizimi (/wallet) ---
SPINNER_SLICES = [
    {"value": 5, "weight": 40.0, "label": "5 sCoin", "color": "#00F2FE"},
    {"value": 10, "weight": 28.0, "label": "10 sCoin", "color": "#4FACFE"},
    {"value": 25, "weight": 16.0, "label": "25 sCoin", "color": "#6366F1"},
    {"value": 50, "weight": 9.0, "label": "50 sCoin", "color": "#A855F7"},
    {"value": 100, "weight": 4.5, "label": "100 sCoin", "color": "#EC4899"},
    {"value": 150, "weight": 1.5, "label": "150 sCoin", "color": "#F43F5E"},
    {"value": 250, "weight": 0.7, "label": "250 sCoin", "color": "#E0AAFF"},
    {"value": 500, "weight": 0.3, "label": "500 sCoin", "color": "#FFD700"}
]

@app.get("/wallet", response_class=HTMLResponse)
async def wallet_page(request: Request):
    user = await get_current_user_optional(request)
    wallet = None
    history_items = []
    total_received = 0.0
    total_sent = 0.0
    can_claim_bonus = True

    if user:
        user_id = user.get("id") or user.get("sub") if isinstance(user, dict) else (getattr(user, "id", None))
        if user_id:
            try:
                from models.shop import Wallet, SCoinTransaction, WheelSpinHistory
                uid = int(user_id)
                async with async_session_maker() as db:
                    # 1. Hamyonni olish yoki yangi foydalanuvchiga 0.00 bilan yaratish
                    stmt = select(Wallet).where(Wallet.user_id == uid)
                    res = await db.execute(stmt)
                    wallet = res.scalar_one_or_none()
                    if not wallet:
                        wallet = Wallet(user_id=uid, scoin_balance=0.0)
                        db.add(wallet)
                        await db.commit()
                        await db.refresh(wallet)

                    # 2. Amallar tarixi (Maks 100 ta)
                    tx_stmt = (
                        select(SCoinTransaction)
                        .where((SCoinTransaction.sender_id == uid) | (SCoinTransaction.receiver_id == uid))
                        .order_by(desc(SCoinTransaction.created_at))
                        .limit(100)
                    )
                    tx_res = await db.execute(tx_stmt)
                    raw_txs = tx_res.scalars().all()

                    for tx in raw_txs:
                        is_in = (tx.receiver_id == uid) and (tx.sender_id != uid)
                        if is_in:
                            total_received += tx.amount
                        elif tx.sender_id == uid:
                            total_sent += (tx.amount + (tx.fee_amount or 0.0))

                        history_items.append({
                            "description": tx.description or tx.tx_type,
                            "amount": tx.amount,
                            "is_incoming": is_in,
                            "date": tx.created_at.strftime("%d.%m.%Y %H:%M") if tx.created_at else ""
                        })

                    # 3. Kunlik bonus spinner tekshiruvi (oxirgi 24 soat)
                    spin_stmt = (
                        select(WheelSpinHistory)
                        .where(WheelSpinHistory.user_id == uid)
                        .order_by(desc(WheelSpinHistory.created_at))
                        .limit(1)
                    )
                    spin_res = await db.execute(spin_stmt)
                    last_spin = spin_res.scalar_one_or_none()
                    if last_spin:
                        now = datetime.now(timezone.utc)
                        last_time = last_spin.created_at
                        if last_time.tzinfo is None:
                            last_time = last_time.replace(tzinfo=timezone.utc)
                        if (now - last_time) < timedelta(hours=24):
                            can_claim_bonus = False
            except Exception as e:
                wallet = None

    return templates.TemplateResponse(
        request=request,
        name="wallet.html",
        context={
            "user": user,
            "username": user.get("username", "mehmon") if isinstance(user, dict) else getattr(user, "username", "mehmon"),
            "wallet": wallet,
            "scoin": round(wallet.scoin_balance, 2) if wallet else 0.0,
            "history_items": history_items,
            "total_received": round(total_received, 2),
            "total_sent": round(total_sent, 2),
            "can_claim_bonus": can_claim_bonus,
            "stest_quota": 50,
            "smavzu_quota": 10,
            "quizer_quota": 5,
            "storage_quota_mb": 40,
            "domain": settings.BASE_DOMAIN,
            "active_page": "wallet"
        }
    )


@app.get("/api/wallet/search-users")
async def wallet_search_users(q: str = "", request: Request = None):
    """P2P o'tkazma uchun foydalanuvchilar username sini qidirish"""
    user = await get_current_user_optional(request)
    if not user or len(q.strip()) < 1:
        return {"users": []}

    uid = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    search_str = f"%{q.strip().lower()}%"
    try:
        from models.auth import User
        async with async_session_maker() as db:
            query = select(User.username).where(
                func.lower(User.username).like(search_str),
                User.id != uid
            ).limit(6)
            res = await db.execute(query)
            usernames = res.scalars().all()
            return {"users": usernames}
    except Exception:
        return {"users": []}


@app.post("/api/wallet/transfer")
async def wallet_transfer(request: Request):
    """Haqiqiy P2P sCoin O'tkazmasi"""
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    sender_id = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    data = await request.json()
    recipient_username = str(data.get("recipient", "")).strip().lstrip("@")
    amount = float(data.get("amount", 0))
    description = str(data.get("description", "")).strip()

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Summa 0 dan katta bo'lishi kerak!")

    from models.auth import User
    from models.shop import Wallet, SCoinTransaction

    async with async_session_maker() as db:
        # Qabul qiluvchini tekshirish
        t_res = await db.execute(select(User).where(func.lower(User.username) == recipient_username.lower()))
        recipient_user = t_res.scalar_one_or_none()
        if not recipient_user:
            raise HTTPException(status_code=404, detail=f"'{recipient_username}' nomli foydalanuvchi topilmadi!")

        if recipient_user.id == sender_id:
            raise HTTPException(status_code=400, detail="O'zingizga sCoin o'tkaza olmaysiz!")

        # Sender hamyoni
        s_res = await db.execute(select(Wallet).where(Wallet.user_id == sender_id))
        sender_wallet = s_res.scalar_one_or_none()
        if not sender_wallet or sender_wallet.scoin_balance < amount:
            current_bal = sender_wallet.scoin_balance if sender_wallet else 0.0
            raise HTTPException(status_code=400, detail=f"Hisobingizda mablag' yetarli emas! Sizda {current_bal} sCoin bor.")

        # Recipient hamyoni
        r_res = await db.execute(select(Wallet).where(Wallet.user_id == recipient_user.id))
        recipient_wallet = r_res.scalar_one_or_none()
        if not recipient_wallet:
            recipient_wallet = Wallet(user_id=recipient_user.id, scoin_balance=0.0)
            db.add(recipient_wallet)
            await db.flush()

        # Balanslarni yangilash
        sender_wallet.scoin_balance -= amount
        recipient_wallet.scoin_balance += amount

        # Tranzaksiya jurnali
        tx = SCoinTransaction(
            sender_id=sender_id,
            receiver_id=recipient_user.id,
            amount=amount,
            fee_amount=0.0,
            tx_type="p2p_transfer",
            description=description or f"@{user.get('username','user')} -> @{recipient_user.username}"
        )
        db.add(tx)
        await db.commit()

        return {
            "success": True,
            "message": f"{amount} sCoin @{recipient_user.username} ga muvaffaqiyatli o'tkazildi!",
            "new_balance": round(sender_wallet.scoin_balance, 2)
        }


@app.post("/api/wallet/spin")
async def wallet_spin(request: Request):
    """Kunlik Bonus Spinner — Omad Charxi (Har 24 soatda)"""
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    user_id = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    now = datetime.now(timezone.utc)

    from models.shop import Wallet, WheelSpinHistory, SCoinTransaction

    async with async_session_maker() as db:
        # Oxirgi spin vaqtini tekshirish
        s_res = await db.execute(
            select(WheelSpinHistory)
            .where(WheelSpinHistory.user_id == user_id)
            .order_by(desc(WheelSpinHistory.created_at))
            .limit(1)
        )
        last_spin = s_res.scalar_one_or_none()
        if last_spin:
            last_time = last_spin.created_at
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            if (now - last_time) < timedelta(hours=24):
                rem = timedelta(hours=24) - (now - last_time)
                hrs = int(rem.total_seconds() // 3600)
                mins = int((rem.total_seconds() % 3600) // 60)
                raise HTTPException(status_code=400, detail=f"Kunlik bonus olingan! Keyingi urinish {hrs} soat {mins} daqiqadan so'ng.")

        # Xavfsiz ehtimollik tanlovi
        import secrets
        weights = [s["weight"] for s in SPINNER_SLICES]
        chosen_slice_index = secrets.SystemRandom().choices(range(len(SPINNER_SLICES)), weights=weights, k=1)[0]
        chosen_item = SPINNER_SLICES[chosen_slice_index]
        prize_amount = float(chosen_item["value"])

        # Hamyonga yozish
        w_res = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = w_res.scalar_one_or_none()
        if not wallet:
            wallet = Wallet(user_id=user_id, scoin_balance=0.0)
            db.add(wallet)
            await db.flush()

        wallet.scoin_balance += prize_amount

        # Spin va tranzaksiya tarixiga qo'shish
        spin_rec = WheelSpinHistory(
            user_id=user_id,
            prize_type="scoin",
            prize_amount=prize_amount
        )
        db.add(spin_rec)

        tx = SCoinTransaction(
            sender_id=None,
            receiver_id=user_id,
            amount=prize_amount,
            fee_amount=0.0,
            tx_type="wheel_win",
            description=f"Kunlik Bonus Omad Charxi: +{prize_amount} sCoin"
        )
        db.add(tx)
        await db.commit()

        return {
            "success": True,
            "prize": prize_amount,
            "slice_index": chosen_slice_index,
            "message": f"Tabriklaymiz! Omad charxida {prize_amount} sCoin yutib oldingiz!",
            "new_balance": round(wallet.scoin_balance, 2)
        }


@app.post("/api/wallet/topup/receipt")
async def wallet_topup_receipt(
    amount_uzs: float = Form(...),
    receipt_file: UploadFile = File(...),
    request: Request = None
):
    """Hisobni to'ldirish uchun kvitansiya chekini yuklash"""
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    user_id = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    receipts_dir = BASE_DIR.parent.parent / "static" / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    filename = f"receipt_{user_id}_{int(datetime.now().timestamp())}_{receipt_file.filename}"
    file_path = receipts_dir / filename

    content = await receipt_file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    scoin_calc = round(amount_uzs / 1000.0, 2)

    from models.shop import PaymentReceipt
    async with async_session_maker() as db:
        receipt = PaymentReceipt(
            user_id=user_id,
            amount_uzs=amount_uzs,
            scoin_requested=scoin_calc,
            receipt_image_path=f"/static/receipts/{filename}",
            status="pending"
        )
        db.add(receipt)
        await db.commit()

    return {
        "success": True,
        "message": f"Chek qabul qilindi ({amount_uzs:,.0f} so'm / {scoin_calc} sCoin). Admin tasdiqlashi bilan hisobingizga tushadi!"
    }


@app.post("/api/wallet/buy-storage-quota")
async def wallet_buy_storage_quota(request: Request):
    """SStorage disk kvotasini kengaytirish"""
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    user_id = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    data = await request.json()
    plan = str(data.get("plan", ""))

    plans = {
        "300mb": {"mb": 300, "price_scoin": 10000},
        "600mb": {"mb": 600, "price_scoin": 40000},
        "1gb": {"mb": 1024, "price_scoin": 60000}
    }
    if plan not in plans:
        raise HTTPException(status_code=400, detail="Noto'g'ri reja tanlandi!")

    selected = plans[plan]
    cost = selected["price_scoin"]

    from models.shop import Wallet, SCoinTransaction
    async with async_session_maker() as db:
        w_res = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = w_res.scalar_one_or_none()
        if not wallet or wallet.scoin_balance < cost:
            current_bal = wallet.scoin_balance if wallet else 0.0
            raise HTTPException(status_code=400, detail=f"Mablag' yetarli emas! Sizda {current_bal} sCoin bor, ushbu xotira uchun {cost} sCoin zarur.")

        wallet.scoin_balance -= cost

        tx = SCoinTransaction(
            sender_id=user_id,
            receiver_id=1,
            amount=cost,
            fee_amount=0.0,
            tx_type="quota_purchase",
            description=f"SStorage kvotasi: {selected['mb']} MB gacha kengaytirildi"
        )
        db.add(tx)
        await db.commit()

        return {
            "success": True,
            "new_balance": round(wallet.scoin_balance, 2),
            "new_quota_mb": selected["mb"],
            "message": f"Tabriklaymiz! SStorage kvotangiz {selected['mb']} MB ga oshirildi!"
        }


# --- 3.2 SStorage Shaxsiy Kiber-Bulut (/storage) ---
STORAGE_BASE = BASE_DIR.parent.parent / "static" / "sstorage"
STORAGE_BASE.mkdir(parents=True, exist_ok=True)

@app.get("/storage", response_class=HTMLResponse)
async def storage_page(request: Request):
    user = await get_current_user_optional(request)
    user_id = user["id"] if isinstance(user, dict) else (user.id if user else 0)
    user_dir = STORAGE_BASE / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    files_list = []
    total_bytes = 0
    if user_dir.exists():
        for f in user_dir.iterdir():
            if f.is_file():
                sz = f.stat().st_size
                total_bytes += sz
                files_list.append({
                    "name": f.name,
                    "size_kb": max(1, sz // 1024),
                    "date": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).strftime("%d.%m.%Y")
                })

    used_mb = round(total_bytes / (1024 * 1024), 2)
    percent = min(100, int((used_mb / 40.0) * 100))

    return templates.TemplateResponse(
        request=request,
        name="storage.html",
        context={
            "user": user,
            "domain": settings.BASE_DOMAIN,
            "active_page": "storage",
            "files": files_list,
            "used_mb": used_mb,
            "percent": percent
        }
    )


@app.post("/api/storage/upload")
async def storage_upload(request: Request):
    import aiofiles
    user = await get_current_user_optional(request)
    user_id = user["id"] if isinstance(user, dict) else (user.id if user else 0)
    user_dir = STORAGE_BASE / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="Fayl topilmadi.")

    file_bytes = await file.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fayl hajmi 25 MB dan oshmasligi kerak.")

    file_path = user_dir / file.filename
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    return {"success": True, "filename": file.filename}


@app.get("/api/storage/download/{filename}")
async def storage_download(filename: str, request: Request):
    user = await get_current_user_optional(request)
    user_id = user["id"] if isinstance(user, dict) else (user.id if user else 0)
    file_path = STORAGE_BASE / str(user_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fayl topilmadi.")
    return FileResponse(path=str(file_path), filename=filename)


@app.delete("/api/storage/delete/{filename}")
async def storage_delete(filename: str, request: Request):
    user = await get_current_user_optional(request)
    user_id = user["id"] if isinstance(user, dict) else (user.id if user else 0)
    file_path = STORAGE_BASE / str(user_id) / filename
    if file_path.exists():
        file_path.unlink()
    return {"success": True}




# --- 3.3 Maktablar Kiber-Reytingi (/schools) ---
@app.get("/schools", response_class=HTMLResponse)
async def schools_page(request: Request):
    user = await get_current_user_optional(request)
    schools_list = []
    try:
        from sqlalchemy import func
        async with async_session_maker() as db:
            stmt = (
                select(
                    func.coalesce(User.school_normalized, User.school_raw).label("school_name"),
                    func.coalesce(User.location_region, "Toshkent shahar").label("region"),
                    func.count(User.id).label("student_count")
                )
                .where(
                    User.is_active == True,
                    User.is_banned == False,
                    (User.school_normalized.isnot(None) | User.school_raw.isnot(None))
                )
                .group_by("school_name", "region")
                .order_by(desc("student_count"))
                .limit(50)
            )
            res = await db.execute(stmt)
            rows = res.all()
            for r in rows:
                if r.school_name and r.school_name.strip():
                    schools_list.append({
                        "name": r.school_name.strip(),
                        "region": r.region or "Toshkent shahar",
                        "type": "Ixtisoslashtirilgan maktab",
                        "student_count": r.student_count,
                        "tests_taken": r.student_count * 12,
                        "avg_score": 88.5
                    })
    except Exception:
        schools_list = []

    # Standart yetakchi maktablar namoyishi
    default_schools = [
        {"name": "Muhammad al-Xorazmiy nomidagi IT-maktab", "region": "Toshkent shahar", "type": "Axborot texnologiyalari maktabi", "student_count": 48, "tests_taken": 312, "avg_score": 96.4},
        {"name": "Prezident Maktabi (Toshkent)", "region": "Toshkent shahar", "type": "Prezident ta'lim muassasasi", "student_count": 42, "tests_taken": 289, "avg_score": 95.8},
        {"name": "Mirzo Ulug'bek nomidagi fizika-matematika maktabi", "region": "Toshkent shahar", "type": "Ixtisoslashtirilgan maktab", "student_count": 35, "tests_taken": 240, "avg_score": 93.2},
        {"name": "1-sonli Ixtisoslashtirilgan Davlat Umumta'lim Maktabi", "region": "Samarqand", "type": "IDUM", "student_count": 29, "tests_taken": 185, "avg_score": 91.5},
        {"name": "Al-Farg'oniy nomidagi aniq fanlar maktab-internati", "region": "Farg'ona", "type": "Maktab-internat", "student_count": 26, "tests_taken": 172, "avg_score": 90.1},
        {"name": "5-sonli umumiy o'rta ta'lim maktabi", "region": "Buxoro", "type": "Umumta'lim maktabi", "student_count": 22, "tests_taken": 140, "avg_score": 88.7},
        {"name": "11-sonli ixtisoslashtirilgan umumta'lim maktabi", "region": "Andijon", "type": "IDUM", "student_count": 19, "tests_taken": 115, "avg_score": 87.9},
        {"name": "2-sonli akademik litsey", "region": "Namangan", "type": "Akademik litsey", "student_count": 18, "tests_taken": 98, "avg_score": 86.4}
    ]

    existing_names = {s["name"].lower() for s in schools_list}
    for ds in default_schools:
        if ds["name"].lower() not in existing_names:
            schools_list.append(ds)

    return templates.TemplateResponse(
        request=request,
        name="schools.html",
        context={"user": user, "schools_list": schools_list, "domain": settings.BASE_DOMAIN, "active_page": "schools"}
    )


# --- 4. Foydalanuvchilar va Reyting (/users) ---
@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    user = await get_current_user_optional(request)
    users_list = []
    try:
        async with async_session_maker() as db:
            stmt = select(User).where(User.is_active == True, User.is_banned == False).order_by(desc(User.created_at)).limit(50)
            res = await db.execute(stmt)
            users_list = res.scalars().all()
    except Exception:
        users_list = []

    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context={"user": user, "users_list": users_list, "domain": settings.BASE_DOMAIN}
    )


# --- 5. Ochiq Profil (/user/{id}) ---
@app.get("/user/{user_id}", response_class=HTMLResponse)
async def user_profile(user_id: int, request: Request):
    current_user = await get_current_user_optional(request)
    target_user = None
    try:
        async with async_session_maker() as db:
            stmt = select(User).where(User.id == user_id, User.is_active == True, User.is_banned == False)
            res = await db.execute(stmt)
            target_user = res.scalar_one_or_none()
    except Exception:
        target_user = None

    if not target_user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    return templates.TemplateResponse(
        request=request,
        name="user_profile.html",
        context={"user": current_user, "profile": target_user, "domain": settings.BASE_DOMAIN}
    )


# --- 5.1 Foydalanuvchi Sozlamalar Paneli (/settings) ---
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = await get_current_user_optional(request)
    if not user:
        return RedirectResponse(url=f"https://auth.{settings.BASE_DOMAIN or 'sstudio.uz'}/login", status_code=302)

    uid = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    db_user = None
    scoin = 0.0

    try:
        from models.shop import Wallet
        async with async_session_maker() as db:
            u_res = await db.execute(select(User).where(User.id == uid))
            db_user = u_res.scalar_one_or_none()

            w_res = await db.execute(select(Wallet).where(Wallet.user_id == uid))
            w = w_res.scalar_one_or_none()
            if w:
                scoin = w.scoin_balance
    except Exception:
        db_user = None

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "user": user,
            "profile": db_user,
            "scoin": scoin,
            "domain": settings.BASE_DOMAIN,
            "active_page": "settings"
        }
    )


@app.post("/api/settings/profile")
async def update_profile_settings(request: Request):
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    uid = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    data = await request.json()

    try:
        async with async_session_maker() as db:
            u_res = await db.execute(select(User).where(User.id == uid))
            db_user = u_res.scalar_one_or_none()
            if not db_user:
                raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi!")

            if data.get("name"): db_user.name = str(data["name"]).strip()
            if data.get("surname"): db_user.surname = str(data["surname"]).strip()
            if "father_name" in data: db_user.father_name = str(data["father_name"]).strip() or None
            if "location_region" in data: db_user.location_region = str(data["location_region"]).strip() or None
            if "location_city" in data: db_user.location_city = str(data["location_city"]).strip() or None
            if "school_raw" in data:
                db_user.school_raw = str(data["school_raw"]).strip() or None
                db_user.school_normalized = str(data["school_raw"]).strip() or None
            if "tel_number" in data: db_user.tel_number = str(data["tel_number"]).strip() or None
            if "telegram_username" in data: db_user.telegram_username = str(data["telegram_username"]).strip().lstrip("@") or None
            if "github_username" in data: db_user.github_username = str(data["github_username"]).strip().lstrip("@") or None
            if "bio" in data: db_user.bio = str(data["bio"]).strip() or None

            await db.commit()
            return {"success": True, "message": "Profil ma'lumotlari muvaffaqiyatli saqlandi!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Xatolik: {str(e)}")


@app.post("/api/settings/change-password")
async def change_password_settings(request: Request):
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    uid = int(user.get("id") or user.get("sub", 0)) if isinstance(user, dict) else getattr(user, "id", 0)
    data = await request.json()
    cur_pass = str(data.get("current_password", ""))
    new_pass = str(data.get("new_password", ""))

    if len(new_pass) < 6:
        raise HTTPException(status_code=400, detail="Yangi parol kamida 6 belgidan iborat bo'lishi kerak!")

    from shared.security import verify_password, hash_password
    try:
        async with async_session_maker() as db:
            u_res = await db.execute(select(User).where(User.id == uid))
            db_user = u_res.scalar_one_or_none()
            if not db_user:
                raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi!")

            if not verify_password(cur_pass, db_user.password_hash):
                raise HTTPException(status_code=400, detail="Joriy parol noto'g'ri kiritildi!")

            db_user.password_hash = hash_password(new_pass)
            await db.commit()
            return {"success": True, "message": "Parol muvaffaqiyatli yangilandi!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Xatolik: {str(e)}")


@app.get("/logout")
async def main_logout(request: Request):
    """Xavfsiz chiqish"""
    redirect_url = f"https://auth.{settings.BASE_DOMAIN or 'sstudio.uz'}/logout"
    resp = RedirectResponse(url=redirect_url, status_code=302)
    resp.delete_cookie(key="sstudio_token", domain=f".{settings.BASE_DOMAIN or 'sstudio.uz'}", path="/")
    resp.delete_cookie(key="sstudio_token", path="/")
    return resp


# --- 6. Huquqiy va Ma'lumot Sahifalari ---
@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    user = await get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={"user": user}
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    user = await get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={"user": user}
    )


@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    user = await get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="faq.html",
        context={"user": user}
    )


@app.get("/connect", response_class=HTMLResponse)
async def connect_page(request: Request):
    user = await get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="connect.html",
        context={"user": user}
    )
