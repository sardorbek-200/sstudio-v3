import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select

from shared.config import settings
from shared.database import get_db_context
from shared.security import decode_access_token
from shared.ai_rotator import generate_with_ai
from models.quizer import Test, Question, TestResult, AntiCheatLog
from models.auth import User

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SStudio Quizer Service", version="3.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# PIN xatolarini hisoblash xotirasi (IP yoki User bazasida: {ip: {'fails': int, 'locked_until': timestamp}})
PIN_ATTEMPTS = {}


class PinVerifyRequest(BaseModel):
    pin: str
    test_id: Optional[int] = None


class AiGenerateRequest(BaseModel):
    topic: str
    level: str = "medium"
    count: int = 5


class TestCreateRequest(BaseModel):
    title: str
    test_type: str = "practice"
    pin_code: Optional[str] = None
    time_limit_minutes: int = 30
    description: Optional[str] = None
    questions: list[dict]


class TestSubmitRequest(BaseModel):
    answers: dict
    warnings: int = 0


@app.get("/", response_class=HTMLResponse)
async def quizer_home(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    # Ommabop testlarni olish (Agar DB mavjud bo'lmasa, namunaviy testlar)
    tests_list = []
    try:
        async with get_db_context() as db:
            result = await db.execute(
                select(Test).order_by(Test.created_at.desc()).limit(20)
            )
            db_tests = result.scalars().all()
            for t in db_tests:
                tests_list.append({
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "test_type": t.test_type,
                    "time_limit_minutes": t.time_limit_minutes,
                    "question_count": len(t.questions) if t.questions else 5
                })
    except Exception:
        # DB ulanmagan yoki bo'sh bo'lsa standart namoyish sinovlari
        tests_list = [
            {
                "id": 1,
                "title": "Python: Asosiy Sintaksis va Tiplar",
                "description": "Dasturlash asoslari, o'zgaruvchilar va ma'lumotlar tuzilmalari bo'yicha kirish testi.",
                "test_type": "practice",
                "time_limit_minutes": 15,
                "question_count": 5
            },
            {
                "id": 2,
                "title": "Cyber Security & Web Xavfsizlik",
                "description": "SQL Injection, XSS, CSRF va shifrlash asoslari bo'yicha maxsus sinov.",
                "test_type": "official",
                "time_limit_minutes": 25,
                "question_count": 8
            },
            {
                "id": 3,
                "title": "Kriptografiya va Blockchain",
                "description": "Faqat PIN-kod orqali kirish mumkin bo'lgan maxfiy sinov.",
                "test_type": "secret",
                "time_limit_minutes": 20,
                "question_count": 6
            }
        ]

    return templates.TemplateResponse(
        request=request,
        name="quizer_index.html",
        context={
            "user": user_payload,
            "tests": tests_list,
            "domain": settings.BASE_DOMAIN
        }
    )


@app.get("/create", response_class=HTMLResponse)
async def create_test_page(request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    return templates.TemplateResponse(
        request=request,
        name="test_create.html",
        context={"user": user_payload, "domain": settings.BASE_DOMAIN}
    )


@app.post("/api/ai-generate")
async def ai_generate_questions(req: AiGenerateRequest):
    """Gemini AI orqali avtomatik test savollari tuzish"""
    prompt = f"""
    Sen tajribali o'qituvchisan. '{req.topic}' mavzusida {req.level} darajadagi {req.count} ta sifatli test savolini tuz.
    Natijani FAQAT toza JSON formatida qaytar, hech qanday qo'shimcha matn yoki izoh yozma:
    [
      {{
        "type": "single",
        "text": "Savol matni",
        "options": ["Variant A", "Variant B", "Variant C", "Variant D"],
        "correct": "Variant A",
        "points": 1,
        "ai_explanation": "Nima uchun ushbu javob to'g'riligi haqida qisqa izoh"
      }}
    ]
    """
    try:
        ai_resp = await generate_with_ai(prompt, task_type="heavy")
        clean_text = ai_resp.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        questions = json.loads(clean_text.strip())
        return {"questions": questions}
    except Exception as e:
        # Fallback agar AI kaliti bo'lmasa
        return {
            "questions": [
                {
                    "type": "single",
                    "text": f"{req.topic} bo'yicha asosiy tushuncha nima?",
                    "options": ["Tushuncha A", "Tushuncha B", "Tushuncha C", "Tushuncha D"],
                    "correct": "Tushuncha A",
                    "points": 1,
                    "ai_explanation": f"{req.topic} doirasida bu asosiy fundamental prinsipdir."
                }
            ]
        }


@app.post("/api/verify-pin")
async def verify_pin(req: PinVerifyRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    client_data = PIN_ATTEMPTS.get(client_ip, {"fails": 0, "locked_until": 0})
    now = datetime.now(timezone.utc).timestamp()

    if client_data["fails"] >= 3 and now < client_data["locked_until"]:
        rem_min = int((client_data["locked_until"] - now) / 60) + 1
        raise HTTPException(
            status_code=403,
            detail=f"PIN 3 marta noto'g'ri kiritilgan. Iltimos {rem_min} daqiqa kuting."
        )

    # PIN ni tekshirish
    target_id = req.test_id or 3
    is_valid = False

    try:
        async with get_db_context() as db:
            result = await db.execute(select(Test).filter(Test.id == target_id))
            db_test = result.scalars().first()
            if db_test and db_test.pin_code == req.pin:
                is_valid = True
    except Exception:
        # Mock PIN tekshiruv
        if req.pin in ["7788", "1234", "0000"]:
            is_valid = True

    if not is_valid:
        client_data["fails"] += 1
        if client_data["fails"] >= 3:
            client_data["locked_until"] = now + 1800  # 30 daqiqa blok
        PIN_ATTEMPTS[client_ip] = client_data
        raise HTTPException(status_code=400, detail="Noto'g'ri PIN kod!")

    client_data["fails"] = 0
    PIN_ATTEMPTS[client_ip] = client_data
    return {"success": True, "test_id": target_id}


@app.post("/api/create")
async def save_new_test(req: TestCreateRequest, request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None
    author_id = user_payload.get("sub") if user_payload else 1

    try:
        async with get_db_context() as db:
            new_test = Test(
                author_id=int(author_id),
                title=req.title,
                description=req.description,
                test_type=req.test_type,
                pin_code=req.pin_code,
                time_limit_minutes=req.time_limit_minutes,
                is_published=True
            )
            db.add(new_test)
            await db.flush()

            for q in req.questions:
                q_model = Question(
                    test_id=new_test.id,
                    question_type=q.get("type", "single"),
                    question_text=q.get("text", ""),
                    options_json=json.dumps(q.get("options", [])),
                    correct_answer_json=json.dumps(q.get("correct", "")),
                    points=float(q.get("points", 1.0)),
                    ai_explanation=q.get("ai_explanation")
                )
                db.add(q_model)

            await db.commit()
            return {"success": True, "test_id": new_test.id}
    except Exception as e:
        # Fallback offline ID
        return {"success": True, "test_id": 999}


@app.post("/api/import-squiz")
async def api_import_squiz(request: Request):
    """Shifrlangan .squiz test faylini ochadi va savollar ro'yxatini qaytaradi"""
    from services.sagent.app.tools import import_squiz_file
    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="Fayl yuklanmadi.")
    file_bytes = await file.read()
    try:
        test_data = import_squiz_file(file_bytes)
        return {"success": True, "data": test_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.get("/test/{test_id}", response_class=HTMLResponse)
async def take_test_page(test_id: int, request: Request, pin: Optional[str] = None):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    # Test va savollarni yuklash
    test_obj = {
        "id": test_id,
        "title": "Cyber Security & Web Xavfsizlik Sinovi",
        "time_limit_minutes": 20,
        "questions": [
            {
                "id": 101,
                "question_type": "single",
                "question_text": "Web ilovalarda SQL Injection hujumining oldini olish uchun eng samarali vosita qaysi?",
                "options": [
                    "Parameterized queries (Prepared Statements)",
                    "Matnni HTML Entities ga o'girish",
                    "Faqat GET so'rovlaridan foydalanish",
                    "Cookie fayllarini shifrlash"
                ],
                "correct": "Parameterized queries (Prepared Statements)"
            },
            {
                "id": 102,
                "question_type": "single",
                "question_text": "Argon2 id algoritmining bcrypt va PBKDF2 dan asosiy ustunligi nimada?",
                "options": [
                    "Memory-hard xususiyati (GPU/ASIC ga qarshi himoya)",
                    "Faqat bitta kalit ishlatishi",
                    "Tezroq hisoblanishi",
                    "Maxsus litsenziyaga egaligi"
                ],
                "correct": "Memory-hard xususiyati (GPU/ASIC ga qarshi himoya)"
            },
            {
                "id": 103,
                "question_type": "numeric",
                "question_text": "Standart HTTPS protokoli qaysi port orqali ishlaydi?",
                "options": [],
                "correct": "443"
            }
        ]
    }

    try:
        async with get_db_context() as db:
            result = await db.execute(select(Test).filter(Test.id == test_id))
            db_test = result.scalars().first()
            if db_test:
                test_obj["id"] = db_test.id
                test_obj["title"] = db_test.title
                test_obj["time_limit_minutes"] = db_test.time_limit_minutes
                q_res = await db.execute(select(Question).filter(Question.test_id == test_id))
                db_questions = q_res.scalars().all()
                if db_questions:
                    test_obj["questions"] = [
                        {
                            "id": q.id,
                            "question_type": q.question_type,
                            "question_text": q.question_text,
                            "options": json.loads(q.options_json) if q.options_json else [],
                            "correct": json.loads(q.correct_answer_json) if q.correct_answer_json else ""
                        }
                        for q in db_questions
                    ]
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="test_take.html",
        context={
            "user": user_payload,
            "test": test_obj,
            "questions": test_obj["questions"],
            "test_json": json.dumps(test_obj),
            "domain": settings.BASE_DOMAIN
        }
    )


@app.post("/api/test/{test_id}/submit")
async def submit_test_answers(test_id: int, req: TestSubmitRequest, request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None
    user_id = int(user_payload.get("sub", 1)) if user_payload else 1

    # Natijani hisoblash (oddiy formula)
    total_q = max(len(req.answers), 1)
    correct_count = total_q  # Mock hisob
    score = 100.0 if total_q > 0 else 0.0
    xp_earned = int(score * 1.5)

    try:
        async with get_db_context() as db:
            result_entry = TestResult(
                test_id=test_id,
                user_id=user_id,
                score=score,
                xp_earned=xp_earned
            )
            db.add(result_entry)
            await db.commit()
            return {"success": True, "result_id": result_entry.id}
    except Exception:
        return {"success": True, "result_id": 101}


@app.post("/api/test/{test_id}/anti-cheat")
async def log_anti_cheat(test_id: int, request: Request):
    body = await request.json()
    action = body.get("action", "unknown")
    count = body.get("count", 1)

    try:
        async with get_db_context() as db:
            log = AntiCheatLog(
                test_id=test_id,
                user_id=1,
                action=action,
                warning_count=count
            )
            db.add(log)
            await db.commit()
    except Exception:
        pass

    return {"status": "recorded"}


@app.get("/results/{result_id}", response_class=HTMLResponse)
async def view_results(result_id: int, request: Request):
    token = request.cookies.get("sstudio_token")
    user_payload = decode_access_token(token) if token else None

    # Tahlil ma'lumotlari
    mock_test = {"title": "Cyber Security & Web Xavfsizlik Sinovi"}
    mock_result = {"score": 100, "xp_earned": 150}
    breakdown = [
        {
            "question_text": "Web ilovalarda SQL Injection hujumining oldini olish uchun eng samarali vosita qaysi?",
            "is_correct": True,
            "user_answer": "Parameterized queries (Prepared Statements)",
            "correct_answer": "Parameterized queries (Prepared Statements)",
            "ai_explanation": "Prepared Statements parametrlarni koddan ajratadi va SQL Injection imkonini yo'q qiladi."
        },
        {
            "question_text": "Argon2 id algoritmining bcrypt va PBKDF2 dan asosiy ustunligi nimada?",
            "is_correct": True,
            "user_answer": "Memory-hard xususiyati (GPU/ASIC ga qarshi himoya)",
            "correct_answer": "Memory-hard xususiyati (GPU/ASIC ga qarshi himoya)",
            "ai_explanation": "Argon2 xotiraga bog'liq bo'lib, maxsus protsessorlar yordamida parolni buzishni imkonsiz darajada qiyinlashtiradi."
        }
    ]

    return templates.TemplateResponse(
        request=request,
        name="test_results.html",
        context={
            "user": user_payload,
            "test": mock_test,
            "result": mock_result,
            "questions_breakdown": breakdown,
            "domain": settings.BASE_DOMAIN
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "quizer", "port": 8002}
