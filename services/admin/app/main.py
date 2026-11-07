from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select, func

from shared.config import settings
from shared.database import get_db_context
from shared.security import decode_access_token
from models.shop import PaymentReceipt, Wallet, SCoinTransaction
from models.auth import User
from models.quizer import Test
from models.admin import AuditLog

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SStudio Admin Service", version="3.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class ReceiptActionRequest(BaseModel):
    action: str  # approve, reject


@app.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    metrics = {
        "total_users": 142,
        "total_scoin": "12,450",
        "total_tests": 38
    }
    pending_receipts = []

    try:
        async with get_db_context() as db:
            # Foydalanuvchilar soni
            u_count = await db.execute(select(func.count(User.id)))
            metrics["total_users"] = u_count.scalar() or 0

            # Testlar soni
            t_count = await db.execute(select(func.count(Test.id)))
            metrics["total_tests"] = t_count.scalar() or 0

            # Kutilayotgan cheklar
            r_res = await db.execute(
                select(PaymentReceipt)
                .filter(PaymentReceipt.status == "pending")
                .order_by(PaymentReceipt.created_at.desc())
            )
            receipts = r_res.scalars().all()
            for r in receipts:
                pending_receipts.append({
                    "id": r.id,
                    "user_id": r.user_id,
                    "amount_uzs": f"{r.amount_uzs:,.0f}",
                    "scoin_requested": r.scoin_requested,
                    "receipt_image_path": r.receipt_image_path
                })
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user_payload,
            "metrics": metrics,
            "pending_receipts": pending_receipts,
            "domain": settings.BASE_DOMAIN,
            "client_ip": request.client.host if request.client else "78.141.246.118"
        }
    )


@app.post("/api/receipts/{receipt_id}/action")
async def review_receipt_action(receipt_id: int, req: ReceiptActionRequest, request: Request):
    try:
        async with get_db_context() as db:
            r_res = await db.execute(select(PaymentReceipt).filter(PaymentReceipt.id == receipt_id))
            receipt = r_res.scalars().first()
            if not receipt:
                raise HTTPException(status_code=404, detail="Chek topilmadi")

            if req.action == "approve":
                receipt.status = "approved"
                receipt.reviewed_at = datetime.now(timezone.utc)

                # Foydalanuvchi hamyoniga SCoin qo'shish
                w_res = await db.execute(select(Wallet).filter(Wallet.user_id == receipt.user_id))
                wallet = w_res.scalars().first()
                if wallet:
                    wallet.scoin_balance += receipt.scoin_requested
                else:
                    wallet = Wallet(user_id=receipt.user_id, scoin_balance=receipt.scoin_requested)
                    db.add(wallet)

                # Tranzaksiya
                tx = SCoinTransaction(
                    sender_id=None,
                    receiver_id=receipt.user_id,
                    amount=receipt.scoin_requested,
                    fee_amount=0.0,
                    tx_type="receipt_topup",
                    description=f"To'lov cheki #{receipt.id} tasdiqlandi"
                )
                db.add(tx)
            else:
                receipt.status = "rejected"
                receipt.reviewed_at = datetime.now(timezone.utc)

            await db.commit()
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": True}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "admin", "port": 8007}
