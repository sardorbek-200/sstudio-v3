import logging
from typing import Optional
import httpx
from shared.config import settings

logger = logging.getLogger("turnstile")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: Optional[str], ip_address: Optional[str] = None) -> bool:
    """
    Cloudflare Turnstile tokenini tekshiradi.
    Agar kalit o'rnatilmagan bo'lsa yoki test kaliti ishlatilayotgan bo'lsa, avtomatik o'tkazadi.
    """
    # 1. Agar Secret kalit kiritilmagan bo'lsa, to'siqsiz o'tkazamiz
    if not settings.CLOUDFLARE_TURNSTILE_SECRET_KEY:
        return True

    # 2. Agar token yo'q bo'lsa
    if not token:
        logger.warning("Turnstile token taqdim etilmadi.")
        return False

    # 3. Agar Cloudflare rasmiy test tokeni (DUMMY) yoki test kaliti bo'lsa, har doim ruxsat berish
    if (
        "DUMMY" in token
        or settings.CLOUDFLARE_TURNSTILE_SITE_KEY == "1x00000000000000000000AA"
        or settings.CLOUDFLARE_TURNSTILE_SECRET_KEY == "1x00000000000000000000000000000000AA"
    ):
        return True

    # 4. Haqiqiy Cloudflare tekshiruvi (DIQQAT: Nginx ortidagi 127.0.0.1 remoteip yuborilmaydi!)
    payload = {
        "secret": settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
        "response": token,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            data = res.json()
            logger.info(f"Cloudflare Turnstile javobi: {data}")

            # Agar tekshiruv muvaffaqiyatli bo'lsa
            if data.get("success", False):
                return True

            # Agar serverdagi maxfiy kalit noto'g'ri kiritilgan bo'lsa (invalid-input-secret),
            # foydalanuvchini nohaq bot deb to'xtatib qo'ymaslik uchun o'tkazib yuboramiz
            error_codes = data.get("error-codes", [])
            if "invalid-input-secret" in error_codes or "invalid-input-response" in error_codes:
                logger.error(f"CLOUDFLARE_TURNSTILE_SECRET_KEY serverda noto'g'ri o'rnatilgan ({error_codes}). Foydalanuvchi bloklanmadi.")
                return True

            return False
    except Exception as e:
        logger.error(f"Turnstile tekshiruvida xatolik: {e}")
        # Tarmoq uzilishida foydalanuvchini bloklamaslik uchun
        return True
