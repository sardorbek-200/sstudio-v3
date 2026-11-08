import logging
from typing import Generator, List, Optional
import google.generativeai as genai
from shared.config import settings

logger = logging.getLogger("ai_rotator")

# Yengil vazifalar (Maktab nomlari, cheklar, qisqa tekshiruvlar)
LIGHT_TASK_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-preview",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

# Chuqur vazifalar (Fayllardan test tuzish, Word/Slayd generatsiyasi, chat)
HEAVY_TASK_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]


class SmartAIRotator:
    def __init__(self):
        self.keys = []
        if settings.GEMINI_API_KEY_1:
            self.keys.append(settings.GEMINI_API_KEY_1)
        if settings.GEMINI_API_KEY_2:
            self.keys.append(settings.GEMINI_API_KEY_2)

    def generate_text(self, prompt: str, task_type: str = "light") -> Optional[str]:
        """
        Oddiy sinxron matn generatsiyasi:
        prompt: Yuboriladigan matn
        task_type: 'light' yoki 'heavy'
        """
        if not self.keys:
            logger.warning("Gemini API kalitlari .env da topilmadi.")
            return None

        model_chain: List[str] = LIGHT_TASK_MODELS if task_type == "light" else HEAVY_TASK_MODELS

        for key_idx, api_key in enumerate(self.keys, 1):
            genai.configure(api_key=api_key)
            for model_name in model_chain:
                try:
                    logger.info(f"AI so'rovi: Kalit {key_idx}, Model: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    error_msg = str(e).lower()
                    if "429" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg or "not_found" in error_msg:
                        logger.warning(f"Limitga uchradi: Kalit {key_idx}, Model: {model_name}. Keyingisiga o'tilmoqda...")
                        continue
                    else:
                        logger.error(f"AI xatosi ({model_name}): {e}")
                        continue

        logger.error("Barcha Gemini kalitlari va modellari bo'yicha limit tugadi yoki xatolik yuz berdi.")
        return None

    def generate_stream(self, prompt: str, task_type: str = "heavy") -> Generator[str, None, None]:
        """
        Server-Sent Events (SSE) uchun oqimli generatsiya:
        Har bir parcha (chunk) chiqqan zahoti yield qilinadi.
        """
        if not self.keys:
            yield "Xatolik: Gemini API kalitlari serverda sozlanmagan."
            return

        model_chain: List[str] = HEAVY_TASK_MODELS if task_type == "heavy" else LIGHT_TASK_MODELS

        for key_idx, api_key in enumerate(self.keys, 1):
            genai.configure(api_key=api_key)
            for model_name in model_chain:
                try:
                    logger.info(f"AI Streaming: Kalit {key_idx}, Model: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt, stream=True)
                    for chunk in response:
                        if chunk and chunk.text:
                            yield chunk.text
                    return
                except Exception as e:
                    error_msg = str(e).lower()
                    if "429" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg or "not_found" in error_msg:
                        logger.warning(f"Stream limit: Kalit {key_idx}, Model: {model_name}. Keyingisiga o'tilmoqda...")
                        continue
                    else:
                        logger.error(f"Stream xatosi ({model_name}): {e}")
                        continue

        yield "Barcha AI modellari band yoki limit tugadi. Birozdan so'ng urinib ko'ring."


ai_rotator = SmartAIRotator()


async def generate_with_ai(prompt: str, task_type: str = "light") -> Optional[str]:
    return ai_rotator.generate_text(prompt, task_type=task_type)
