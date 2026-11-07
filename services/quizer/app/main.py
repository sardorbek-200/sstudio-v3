from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from shared.config import settings
from shared.security import decode_access_token

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SStudio Quizer Service", version="3.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def quizer_home(request: Request):
    # SSO token orqali foydalanuvchini tekshirish
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    return templates.TemplateResponse(
        request=request,
        name="quizer_index.html",
        context={"user": user_payload, "domain": settings.BASE_DOMAIN}
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "quizer", "port": 8002}
