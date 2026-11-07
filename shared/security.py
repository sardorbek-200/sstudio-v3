from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from shared.config import settings

# Argon2 Password Hasher
ph = PasswordHasher()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Parolni Argon2 algoritmi bilan xavfsiz hashlaydi"""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parol to'g'riligini tekshiradi"""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """30 kunlik yoki ko'rsatilgan muddatli JWT token yaratadi"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=30)  # 30 kunlik sessiya

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT tokenni tekshiradi va ichidagi ma'lumotni qaytaradi"""
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
