import logging
from typing import List, Optional
import google.generativeai as genai
from shared.config import settings

logger = logging.getLogger("ai_rotator")

# Yengil vazifalar (Maktab nomlari, cheklar, qisqa tekshiruvlar)
LIGHT_TASK_MODELS = [
    "gemini-1.5-flash",
    "gemini-2.0-flash-lite-preview",
    "gemini-1.5-flash-8b",
]

# Chuqur vazifalar (Fayllardan test tuzish, AI baholash)
HEAVY_TASK_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-pro",
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
        prompt: Yuboriladigan matn
        task_type: 'light' (yengil/maktablar) yoki 'heavy' (test tuzish)
        Avtomatik ravishda Kalit 1 -> Modellar -> Kalit 2 -> Modellar bo'yicha aylanadi.
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
                    if "429" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg:
                        logger.warning(f"Limitga uchradi: Kalit {key_idx}, Model: {model_name}. Keyingisiga o'tilmoqda...")
                        continue
                    else:
                        logger.error(f"AI xatosi ({model_name}): {e}")
                        continue

        logger.error("Barcha Gemini kalitlari va modellari bo'yicha limit tugadi yoki xatolik yuz berdi.")
        return None


ai_rotator = SmartAIRotator()
