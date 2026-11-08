import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth import Session as DbSession, User
from services.auth.app.schemas import LoginRequest, RegisterRequest
from shared.ai_rotator import ai_rotator
from shared.config import settings
from shared.database import get_db
from shared.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from shared.turnstile import verify_turnstile_token

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SStudio Auth Service", version="3.0.0")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- Sahifalar (HTML) ---

@app.get("/", response_class=RedirectResponse)
async def home_redirect():
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sign-in.html",
        context={
            "domain": settings.BASE_DOMAIN,
            "turnstile_site_key": settings.CLOUDFLARE_TURNSTILE_SITE_KEY or ""
        }
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sign-up.html",
        context={
            "domain": settings.BASE_DOMAIN,
            "turnstile_site_key": settings.CLOUDFLARE_TURNSTILE_SITE_KEY or ""
        }
    )


# --- API / Amallar ---

@app.post("/api/register")
@app.post("/register")
async def api_register(
    req: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # Cloudflare Turnstile Bot Tekshiruvi
    client_ip = request.client.host if request.client else None
    is_human = await verify_turnstile_token(req.cf_turnstile_response, client_ip)
    if not is_human:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot tekshiruvidan o'tmadingiz (Cloudflare Turnstile)"
        )

    # Username yoki email bandligini tekshirish
    stmt = select(User).where(
        or_(
            User.username == req.username,
            (User.gmail == req.gmail) if req.gmail else False
        )
    )
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ushbu username yoki email allaqachon ro'yxatdan o'tgan"
        )

    # Maktab nomini AI orqali normallashtirish (agar kiritilgan bo'lsa)
    school_norm = None
    if req.school_raw:
        prompt = (
            f"Foydalanuvchi maktabi: '{req.school_raw}'. "
            "Ushbu ta'lim muassasasi nomini O'zbekiston standartiga mos qisqa va rasmiy shaklga keltirib faqat nomini qaytar. "
            "Masalan: 'Toshkent shahar 1-sonli maktab' yoki 'Toshkent Axborot Texnologiyalari Universiteti'. Faqat bitta nom qaytar."
        )
        ai_res = ai_rotator.generate_text(prompt, task_type="light")
        school_norm = ai_res if ai_res else req.school_raw

    # Yangi user yaratish
    new_user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        name=req.name,
        surname=req.surname,
        father_name=req.father_name,
        birthday=req.birthday,
        location_region=req.location_region,
        location_city=req.location_city,
        school_raw=req.school_raw,
        school_normalized=school_norm,
        school_type=req.school_type,
        gmail=req.gmail,
        tel_number=req.tel_number,
        status="freemium",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Sessiya yaratish (30 kunlik)
    token = create_access_token({
        "sub": str(new_user.id),
        "username": new_user.username,
        "name": new_user.name,
        "surname": new_user.surname,
        "status": new_user.status
    })
    token_hash = get_token_hash(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    session_entry = DbSession(
        user_id=new_user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info="Web Browser",
    )
    db.add(session_entry)
    await db.commit()

    # Cookie o'rnatish (.sstudio.uz barcha subdomenlar uchun)
    cookie_domain = None if "localhost" in settings.BASE_DOMAIN else f".{settings.BASE_DOMAIN}"
    response.set_cookie(
        key="sstudio_token",
        value=token,
        max_age=30 * 86400,
        httponly=True,
        secure=True if settings.APP_ENV == "production" else False,
        samesite="lax",
        domain=cookie_domain
    )

    return {"status": "ok", "message": "Muvaffaqiyatli ro'yxatdan o'tdingiz", "user_id": new_user.id}


@app.post("/api/login")
@app.post("/login")
async def api_login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # Cloudflare Turnstile Bot Tekshiruvi
    client_ip = request.client.host if request.client else None
    is_human = await verify_turnstile_token(req.cf_turnstile_response, client_ip)
    if not is_human:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot tekshiruvidan o'tmadingiz (Cloudflare Turnstile)"
        )

    stmt = select(User).where(
        or_(
            User.username == req.username_or_email,
            User.gmail == req.username_or_email
        )
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/Email yoki parol noto'g'ri"
        )

    if user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akkauntingiz bloklangan")

    # Token va DB sessiya
    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "name": user.name,
        "surname": user.surname,
        "status": user.status
    })
    token_hash = get_token_hash(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    session_entry = DbSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info="Web Browser",
    )
    db.add(session_entry)
    await db.commit()

    cookie_domain = None if "localhost" in settings.BASE_DOMAIN else f".{settings.BASE_DOMAIN}"
    response.set_cookie(
        key="sstudio_token",
        value=token,
        max_age=30 * 86400,
        httponly=True,
        secure=True if settings.APP_ENV == "production" else False,
        samesite="lax",
        domain=cookie_domain
    )

    return {"status": "ok", "message": "Xush kelibsiz", "user": {"id": user.id, "username": user.username}}


@app.get("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("sstudio_token")
    if token:
        token_hash = get_token_hash(token)
        stmt = select(DbSession).where(DbSession.token_hash == token_hash)
        res = await db.execute(stmt)
        sess = res.scalar_one_or_none()
        if sess:
            await db.delete(sess)
            await db.commit()

    cookie_domain = None if "localhost" in settings.BASE_DOMAIN else f".{settings.BASE_DOMAIN}"
    response = RedirectResponse(url="/login")
    response.delete_cookie("sstudio_token", domain=cookie_domain)
    return response


@app.get("/internal/verify")
async def internal_verify(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("sstudio_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Token mavjud emas")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token yaroqsiz yoki muddati o'tgan")

    token_hash = get_token_hash(token)
    stmt = select(DbSession).where(
        DbSession.token_hash == token_hash,
        DbSession.expires_at > datetime.now(timezone.utc)
    )
    res = await db.execute(stmt)
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=401, detail="Faol sessiya topilmadi")

    stmt_user = select(User).where(User.id == sess.user_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()
    if not user or not user.is_active or user.is_banned:
        raise HTTPException(status_code=403, detail="Foydalanuvchi faol emas")

    return {
        "user_id": user.id,
        "username": user.username,
        "name": user.name,
        "surname": user.surname,
        "status": user.status,
    }
