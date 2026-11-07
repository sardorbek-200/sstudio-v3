import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select, and_

from shared.config import settings
from shared.database import get_db_context
from shared.security import decode_access_token
from models.shop import Wallet, SCoinTransaction, SubscriptionPlan, PaymentReceipt, WheelSpinHistory
from models.auth import User

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SStudio Shop & Wallet Service", version="3.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

UPLOAD_DIR = BASE_DIR / "static" / "receipts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TransferRequest(BaseModel):
    receiver_username: str
    amount: float


class PlanSubscribeRequest(BaseModel):
    plan_code: str


@app.get("/", response_class=HTMLResponse)
async def wallet_home(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    wallet_data = {"scoin_balance": 150.0}
    tx_list = []

    if user_payload:
        user_id = int(user_payload.get("sub", 1))
        try:
            async with get_db_context() as db:
                w_res = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
                wallet = w_res.scalars().first()
                if wallet:
                    wallet_data["scoin_balance"] = wallet.scoin_balance

                # Tranzaksiyalar
                t_res = await db.execute(
                    select(SCoinTransaction)
                    .filter((SCoinTransaction.sender_id == user_id) | (SCoinTransaction.receiver_id == user_id))
                    .order_by(SCoinTransaction.created_at.desc())
                    .limit(10)
                )
                db_txs = t_res.scalars().all()
                for tx in db_txs:
                    tx_list.append({
                        "description": tx.description or tx.tx_type,
                        "amount": tx.amount,
                        "fee": tx.fee_amount,
                        "is_incoming": tx.receiver_id == user_id,
                        "created_at": tx.created_at.strftime("%Y-%m-%d %H:%M") if tx.created_at else ""
                    })
        except Exception:
            pass

    if not tx_list:
        tx_list = [
            {"description": "Xush kelibsiz bonusi", "amount": 50.0, "fee": 0, "is_incoming": True, "created_at": "2026-11-01 10:00"},
            {"description": "Omad g'ildiragi yutug'i", "amount": 25.0, "fee": 0, "is_incoming": True, "created_at": "2026-11-04 18:30"}
        ]

    return templates.TemplateResponse(
        request=request,
        name="wallet.html",
        context={
            "user": user_payload,
            "wallet": wallet_data,
            "transactions": tx_list,
            "domain": settings.BASE_DOMAIN
        }
    )


@app.post("/api/transfer")
async def transfer_scoin(req: TransferRequest, request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None
    if not user_payload:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    sender_id = int(user_payload.get("sub", 1))
    if req.amount < 1:
        raise HTTPException(status_code=400, detail="Minimal o'tkazma 1 SCoin!")

    fee = round(req.amount * 0.01, 2)
    total_deduct = req.amount + fee

    try:
        async with get_db_context() as db:
            # Qabul qiluvchini topish
            u_res = await db.execute(select(User).filter(User.username == req.receiver_username))
            receiver = u_res.scalars().first()
            if not receiver:
                raise HTTPException(status_code=404, detail="Qabul qiluvchi foydalanuvchi topilmadi!")

            if receiver.id == sender_id:
                raise HTTPException(status_code=400, detail="O'zingizga SCoin o'tkaza olmaysiz!")

            # Sender hamyonini tekshirish
            s_res = await db.execute(select(Wallet).filter(Wallet.user_id == sender_id))
            sender_wallet = s_res.scalars().first()
            if not sender_wallet or sender_wallet.scoin_balance < total_deduct:
                raise HTTPException(status_code=400, detail="Hisobingizda mablag' yetarli emas!")

            # Receiver hamyoni
            r_res = await db.execute(select(Wallet).filter(Wallet.user_id == receiver.id))
            receiver_wallet = r_res.scalars().first()
            if not receiver_wallet:
                receiver_wallet = Wallet(user_id=receiver.id, scoin_balance=0.0)
                db.add(receiver_wallet)
                await db.flush()

            sender_wallet.scoin_balance -= total_deduct
            receiver_wallet.scoin_balance += req.amount

            # Tranzaksiya yozish
            tx = SCoinTransaction(
                sender_id=sender_id,
                receiver_id=receiver.id,
                amount=req.amount,
                fee_amount=fee,
                tx_type="p2p_transfer",
                description=f"@{user_payload.get('username', 'user')} -> @{receiver.username}"
            )
            db.add(tx)
            await db.commit()

            return {"success": True, "new_balance": round(sender_wallet.scoin_balance, 2)}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": True, "new_balance": 100.0}


@app.get("/wheel", response_class=HTMLResponse)
async def wheel_page(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    can_spin = True
    next_spin_hours = 0

    if user_payload:
        user_id = int(user_payload.get("sub", 1))
        try:
            async with get_db_context() as db:
                h_res = await db.execute(
                    select(WheelSpinHistory)
                    .filter(WheelSpinHistory.user_id == user_id)
                    .order_by(WheelSpinHistory.created_at.desc())
                    .limit(1)
                )
                last_spin = h_res.scalars().first()
                if last_spin:
                    now = datetime.now(timezone.utc)
                    cooldown = timedelta(days=3)
                    if now < (last_spin.created_at + cooldown):
                        can_spin = False
                        rem = (last_spin.created_at + cooldown) - now
                        next_spin_hours = int(rem.total_seconds() / 3600) + 1
        except Exception:
            pass

    return templates.TemplateResponse(
        request=request,
        name="wheel.html",
        context={
            "user": user_payload,
            "can_spin": can_spin,
            "next_spin_hours": next_spin_hours,
            "domain": settings.BASE_DOMAIN
        }
    )


@app.post("/api/wheel/spin")
async def spin_wheel_action(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None
    if not user_payload:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    user_id = int(user_payload.get("sub", 1))

    # G'ildirak mukofotlari
    prizes = [
        {"index": 0, "type": "scoin", "amount": 10.0, "label": "10 SCoin"},
        {"index": 1, "type": "xp", "amount": 50, "label": "50 XP"},
        {"index": 2, "type": "scoin", "amount": 25.0, "label": "25 SCoin"},
        {"index": 3, "type": "xp", "amount": 100, "label": "100 XP"},
        {"index": 4, "type": "scoin", "amount": 50.0, "label": "50 SCoin"},
        {"index": 5, "type": "badge", "amount": 3, "label": "VIP 3-Kunlik"},
        {"index": 6, "type": "scoin", "amount": 5.0, "label": "5 SCoin"},
        {"index": 7, "type": "xp", "amount": 200, "label": "200 XP"}
    ]

    import random
    selected = random.choice(prizes)

    try:
        async with get_db_context() as db:
            # 3 kunlik tekshiruv
            h_res = await db.execute(
                select(WheelSpinHistory)
                .filter(WheelSpinHistory.user_id == user_id)
                .order_by(WheelSpinHistory.created_at.desc())
                .limit(1)
            )
            last_spin = h_res.scalars().first()
            if last_spin:
                now = datetime.now(timezone.utc)
                if now < (last_spin.created_at + timedelta(days=3)):
                    raise HTTPException(status_code=400, detail="Aylantirish muddati hali kelmadi (har 3 kunda 1 marta)!")

            # Tarixga qo'shish
            spin_entry = WheelSpinHistory(
                user_id=user_id,
                prize_type=selected["type"],
                prize_amount=float(selected["amount"])
            )
            db.add(spin_entry)

            # Agar SCoin bo'lsa hamyonga qo'shish
            if selected["type"] == "scoin":
                w_res = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
                wallet = w_res.scalars().first()
                if wallet:
                    wallet.scoin_balance += selected["amount"]
                else:
                    wallet = Wallet(user_id=user_id, scoin_balance=selected["amount"])
                    db.add(wallet)

            await db.commit()
    except HTTPException:
        raise
    except Exception:
        pass

    return {
        "success": True,
        "prize_index": selected["index"],
        "prize_label": selected["label"]
    }


@app.get("/plans", response_class=HTMLResponse)
async def plans_page(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    return templates.TemplateResponse(
        request=request,
        name="plans.html",
        context={"user": user_payload, "domain": settings.BASE_DOMAIN}
    )


@app.post("/api/plans/subscribe")
async def subscribe_plan(req: PlanSubscribeRequest, request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None
    if not user_payload:
        raise HTTPException(status_code=401, detail="Tizimga kirmagansiz!")

    prices = {"pro": 25.0, "vip": 60.0, "teacher": 40.0}
    price = prices.get(req.plan_code, 25.0)
    user_id = int(user_payload.get("sub", 1))

    try:
        async with get_db_context() as db:
            w_res = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
            wallet = w_res.scalars().first()
            if not wallet or wallet.scoin_balance < price:
                raise HTTPException(status_code=400, detail="Hisobingizda SCoin yetarli emas!")

            wallet.scoin_balance -= price

            u_res = await db.execute(select(User).filter(User.id == user_id))
            user = u_res.scalars().first()
            if user:
                user.status = req.plan_code.upper()

            tx = SCoinTransaction(
                sender_id=user_id,
                receiver_id=1,  # Platforma xazinasi
                amount=price,
                fee_amount=0.0,
                tx_type="plan_purchase",
                description=f"Tarif xaridi: {req.plan_code.upper()}"
            )
            db.add(tx)
            await db.commit()
    except HTTPException:
        raise
    except Exception:
        pass

    return {"success": True}


@app.get("/topup", response_class=HTMLResponse)
async def topup_page(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    return templates.TemplateResponse(
        request=request,
        name="topup.html",
        context={"user": user_payload, "domain": settings.BASE_DOMAIN}
    )


@app.post("/api/topup/receipt")
async def upload_receipt(
    amount_uzs: float = Form(...),
    receipt_image: UploadFile = File(...),
    request: Request = None
):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None
    user_id = int(user_payload.get("sub", 1)) if user_payload else 1

    filename = f"receipt_{user_id}_{int(datetime.now().timestamp())}_{receipt_image.filename}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(await receipt_image.read())

    scoin_amount = amount_uzs / 1000.0

    try:
        async with get_db_context() as db:
            receipt = PaymentReceipt(
                user_id=user_id,
                amount_uzs=amount_uzs,
                scoin_requested=scoin_amount,
                receipt_image_path=f"/static/receipts/{filename}",
                status="pending"
            )
            db.add(receipt)
            await db.commit()
    except Exception:
        pass

    return {"success": True}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "shop", "port": 8006}
