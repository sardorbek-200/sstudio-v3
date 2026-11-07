import logging
from typing import Optional
import httpx
from shared.config import settings

logger = logging.getLogger("turnstile")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: Optional[str], ip_address: Optional[str] = None) -> bool:
    """
    Cloudflare Turnstile tokenini tekshiradi.
    Agar development rejimida bo'lsa yoki kalit o'rnatilmagan bo'lsa, o'tkazib yuboradi.
    """
    # Agar kalit hali .env da bo'lmasa yoki dev muhitida bo'lsak, xalaqit bermaydi
    if not settings.CLOUDFLARE_TURNSTILE_SECRET_KEY:
        return True

    if not token:
        logger.warning("Turnstile token taqdim etilmadi.")
        return False

    payload = {
        "secret": settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if ip_address:
        payload["remoteip"] = ip_address

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            data = res.json()
            return data.get("success", False)
    except Exception as e:
        logger.error(f"Turnstile tekshiruvida xatolik: {e}")
        # Server xatoligida foydalanuvchini bloklamaslik uchun:
        return False
