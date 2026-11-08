import os
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.config import settings
from shared.database import get_db
from shared.security import get_current_user_optional, get_current_user
from shared.ai_rotator import ai_rotator
from services.sagent.app.tools import (
    generate_word_document,
    generate_presentation_slides,
    export_squiz_file,
    import_squiz_file
)

logger = logging.getLogger("sagent")

app = FastAPI(
    title="SStudio SAgent AI Service",
    description="Markaziy Sun'iy Intellekt, STest, SMavzu va Agentic Tool Generatori",
    version="3.0.0-PRO"
)

# Template va Static yo'llari
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)


# =========================================================================
# SCHEMAS
# =========================================================================

class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: Optional[List[ChatMessage]] = []
    task_type: Optional[str] = "heavy"


class DocGenerateRequest(BaseModel):
    title: str
    sections: List[Dict[str, Any]]
    filename: Optional[str] = "konspekt.docx"


class SlideGenerateRequest(BaseModel):
    title: str
    slides: List[Dict[str, Any]]
    filename: Optional[str] = "taqdimot.pptx"


class SquizGenerateRequest(BaseModel):
    test_title: str
    subject: str
    duration_minutes: int = 20
    questions: List[Dict[str, Any]]
    filename: Optional[str] = "test.squiz"


# =========================================================================
# WEB ROUTES
# =========================================================================

@app.get("/", response_class=HTMLResponse)
async def sagent_dashboard(
    request: Request,
    user=Depends(get_current_user_optional)
):
    """SAgent Kiber-Chat Interfeysi"""
    return templates.TemplateResponse(
        request=request,
        name="sagent_chat.html",
        context={
            "user": user,
            "domain": settings.BASE_DOMAIN,
            "active_page": "sagent"
        }
    )


# =========================================================================
# STREAMING SSE CHAT ENDPOINT
# =========================================================================

@app.post("/api/chat")
async def chat_stream_endpoint(
    req: ChatRequest,
    user=Depends(get_current_user_optional)
):
    """
    ChatGPT/Claude kabi real-time oqimli (SSE) javob beruvchi endpoint.
    Har bir belgi kelishi bilan ekranda yoziladi.
    """
    prompt = req.message

    def event_stream():
        # Dastlabki ulanganlik xabari
        yield f"data: {json.dumps({'status': 'connected'})}\n\n"

        for text_chunk in ai_rotator.generate_stream(prompt, task_type="heavy"):
            data = {"chunk": text_chunk}
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'status': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# =========================================================================
# AGENTIC TOOL GENERATORS (Word, Slayd, .squiz)
# =========================================================================

@app.post("/api/tools/generate-doc")
async def api_generate_word(
    req: DocGenerateRequest,
    user=Depends(get_current_user_optional)
):
    """SAgent foydalanuvchi buyrug'i bo'yicha haqiqiy Word (.docx) yaratadi"""
    user_id = user.id if user else 0
    file_path = generate_word_document(
        title=req.title,
        sections=req.sections,
        user_id=user_id,
        filename=req.filename or "konspekt.docx"
    )
    return {
        "success": True,
        "filename": os.path.basename(file_path),
        "download_url": f"/api/storage/download/{user_id}/{os.path.basename(file_path)}"
    }


@app.post("/api/tools/generate-slides")
async def api_generate_slides(
    req: SlideGenerateRequest,
    user=Depends(get_current_user_optional)
):
    """SAgent taqdimot (.pptx) yaratadi"""
    user_id = user.id if user else 0
    file_path = generate_presentation_slides(
        title=req.title,
        slides=req.slides,
        user_id=user_id,
        filename=req.filename or "taqdimot.pptx"
    )
    return {
        "success": True,
        "filename": os.path.basename(file_path),
        "download_url": f"/api/storage/download/{user_id}/{os.path.basename(file_path)}"
    }


@app.post("/api/tools/generate-squiz")
async def api_generate_squiz(
    req: SquizGenerateRequest,
    user=Depends(get_current_user_optional)
):
    """Quizer uchun shifrlangan .squiz test fayli generatsiya qiladi"""
    user_id = user.id if user else 0
    test_data = {
        "title": req.test_title,
        "subject": req.subject,
        "duration_minutes": req.duration_minutes,
        "questions": req.questions
    }
    file_path = export_squiz_file(test_data, user_id=user_id, filename=req.filename or "test.squiz")
    return {
        "success": True,
        "filename": os.path.basename(file_path),
        "download_url": f"/api/storage/download/{user_id}/{os.path.basename(file_path)}"
    }


# =========================================================================
# FAYLLARNI YUKLAB OLISH (STORAGE DOWNLOAD)
# =========================================================================

@app.get("/api/storage/download/{user_id}/{filename}")
async def download_storage_file(user_id: int, filename: str):
    """SStorage dagi generatsiya qilingan faylni yuklab olish"""
    from services.sagent.app.tools import STORAGE_DIR
    file_path = os.path.join(STORAGE_DIR, str(user_id), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fayl topilmadi.")
    return FileResponse(path=file_path, filename=filename)


# =========================================================================
# DEVELOPER PUBLIC API (sk_live_...)
# =========================================================================

@app.post("/v1/chat/completions")
async def developer_public_api(
    req: ChatRequest,
    request: Request
):
    """
    Tashqi dasturchilar va ta'lim muassasalari uchun ochiq SAgent API.
    Rate limit: 10 so'rov/daqiqa, 20K token freemium.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer sk_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yaroqsiz API kalit. Kalit 'Bearer sk_live_...' shaklida bo'lishi kerak."
        )

    ai_reply = ai_rotator.generate_text(req.message, task_type="heavy")
    if not ai_reply:
        raise HTTPException(status_code=500, detail="AI xizmati vaqtincha javob bermadi.")

    return {
        "id": "chatcmpl-sagent-v3",
        "object": "chat.completion",
        "model": "sagent-gemini-hypercore",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": ai_reply
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(req.message) // 4,
            "completion_tokens": len(ai_reply) // 4,
            "total_tokens": (len(req.message) + len(ai_reply)) // 4
        }
    }
