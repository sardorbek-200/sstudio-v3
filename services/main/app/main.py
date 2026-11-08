from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select

from models.auth import User
from shared.config import settings
from shared.database import async_session_maker
from shared.security import decode_access_token

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SStudio Main Portal", version="3.0.0")

# Statik fayllar va Shablonlar
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
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


# --- 3.1 Hamyon va Kiber-Tariflar (/wallet) ---
@app.get("/wallet", response_class=HTMLResponse)
async def wallet_page(request: Request):
    user = await get_current_user_optional(request)
    return templates.TemplateResponse(
        request=request,
        name="wallet.html",
        context={"user": user, "domain": settings.BASE_DOMAIN, "active_page": "wallet"}
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
