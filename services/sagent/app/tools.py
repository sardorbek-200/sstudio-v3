import os
import json
import base64
import logging
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet
from shared.config import settings

logger = logging.getLogger("sagent.tools")

# SStudio Kiber-Kaliti (squiz shifrlash uchun 32 bayt)
DEFAULT_FERNET_KEY = base64.urlsafe_b64encode(b"sstudio_v3_super_secret_cipher32")
CIPHER_SUITE = Fernet(DEFAULT_FERNET_KEY)

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "sstorage")
os.makedirs(STORAGE_DIR, exist_ok=True)


def ensure_user_storage_dir(user_id: int) -> str:
    user_dir = os.path.join(STORAGE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


# =========================================================================
# 1. SHIFRLANGAN .SQUIZ TEST FORMATI (Quizer uchun)
# =========================================================================

def export_squiz_file(test_data: Dict[str, Any], user_id: int, filename: str = "test.squiz") -> str:
    """
    Test ma'lumotlarini (savollar, variantlar, to'g'ri javoblar) shifrlab
    .squiz fayl qilib foydalanuvchining sstorage papkasiga saqlaydi.
    """
    user_dir = ensure_user_storage_dir(user_id)
    if not filename.endswith(".squiz"):
        filename += ".squiz"
    file_path = os.path.join(user_dir, filename)

    raw_json = json.dumps(test_data, ensure_ascii=False, indent=2).encode("utf-8")
    encrypted_bytes = CIPHER_SUITE.encrypt(raw_json)

    with open(file_path, "wb") as f:
        f.write(encrypted_bytes)

    logger.info(f".squiz fayl muvaffaqiyatli saqlandi: {file_path}")
    return file_path


def import_squiz_file(file_bytes: bytes) -> Dict[str, Any]:
    """
    Shifrlangan .squiz faylini ochadi va Quizer uchun JSON lug'atga aylantiradi.
    """
    try:
        decrypted_json = CIPHER_SUITE.decrypt(file_bytes)
        return json.loads(decrypted_json.decode("utf-8"))
    except Exception as e:
        logger.error(f".squiz faylni deshifrlashda xatolik: {e}")
        raise ValueError("Yaroqsiz yoki buzilgan .squiz test fayli.")


# =========================================================================
# 2. HAQIQIY WORD (.DOCX) GENERATORI
# =========================================================================

def generate_word_document(
    title: str,
    sections: List[Dict[str, Any]],
    user_id: int,
    filename: str = "konspekt.docx"
) -> str:
    """
    Foydalanuvchi buyrug'i bo'yicha chiroyli formatlangan Word (.docx) fayl yasaydi.
    sections: [{'heading': '...', 'content': '...', 'bullets': [...]}]
    """
    user_dir = ensure_user_storage_dir(user_id)
    if not filename.endswith(".docx"):
        filename += ".docx"
    file_path = os.path.join(user_dir, filename)

    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor

        doc = Document()
        # Sarlavha
        h1 = doc.add_heading(title, level=0)
        h1.style.font.name = 'Arial'

        for sec in sections:
            if "heading" in sec and sec["heading"]:
                doc.add_heading(sec["heading"], level=1)
            if "content" in sec and sec["content"]:
                p = doc.add_paragraph(sec["content"])
                p.style.font.size = Pt(11)
            if "bullets" in sec and isinstance(sec["bullets"], list):
                for bullet in sec["bullets"]:
                    doc.add_paragraph(bullet, style='List Bullet')

        doc.save(file_path)
        logger.info(f"Word hujjat yaratildi: {file_path}")
        return file_path
    except ImportError:
        # python-docx hali o'rnatilmagan bo'lsa zaxira matnli fayl
        txt_path = file_path.replace(".docx", ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"=== {title} ===\n\n")
            for sec in sections:
                f.write(f"\n## {sec.get('heading', '')}\n")
                f.write(f"{sec.get('content', '')}\n")
        return txt_path


# =========================================================================
# 3. HAQIQIY POWERPOINT (.PPTX) GENERATORI
# =========================================================================

def generate_presentation_slides(
    title: str,
    slides: List[Dict[str, Any]],
    user_id: int,
    filename: str = "taqdimot.pptx"
) -> str:
    """
    Slaydlar ketma-ketligini PowerPoint (.pptx) faylga aylantiradi.
    slides: [{'title': '...', 'bullets': ['...', '...']}]
    """
    user_dir = ensure_user_storage_dir(user_id)
    if not filename.endswith(".pptx"):
        filename += ".pptx"
    file_path = os.path.join(user_dir, filename)

    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor

        prs = Presentation()
        # Birinchi bosh slayd
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title_shape = slide.shapes.title
        subtitle_shape = slide.placeholders[1]
        title_shape.text = title
        subtitle_shape.text = "SStudio SAgent orqali avtomatik generatsiya qilingan"

        # Qolgan kontent slaydlari
        bullet_slide_layout = prs.slide_layouts[1]
        for s in slides:
            b_slide = prs.slides.add_slide(bullet_slide_layout)
            shapes = b_slide.shapes
            title_box = shapes.title
            body_box = shapes.placeholders[1]
            title_box.text = s.get("title", "Slayd")

            tf = body_box.text_frame
            bullets = s.get("bullets", [])
            for i, b in enumerate(bullets):
                if i == 0:
                    tf.text = b
                else:
                    p = tf.add_paragraph()
                    p.text = b

        prs.save(file_path)
        logger.info(f"PowerPoint taqdimot yaratildi: {file_path}")
        return file_path
    except ImportError:
        txt_path = file_path.replace(".pptx", ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"=== TAQDIMOT: {title} ===\n\n")
            for s in slides:
                f.write(f"\n[SLAYD]: {s.get('title', '')}\n")
                for b in s.get("bullets", []):
                    f.write(f"  * {b}\n")
        return txt_path
