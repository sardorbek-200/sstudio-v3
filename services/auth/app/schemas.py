from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2, max_length=100)
    surname: str = Field(..., min_length=2, max_length=100)
    father_name: Optional[str] = None
    birthday: Optional[date] = None

    # Joylashuv
    location_region: Optional[str] = None
    location_city: Optional[str] = None

    # Ta'lim
    school_raw: Optional[str] = None
    school_type: Optional[str] = "school"

    # Aloqa
    gmail: Optional[EmailStr] = None
    tel_number: Optional[str] = None

    # Bot himoyasi (Cloudflare Turnstile token)
    cf_turnstile_response: Optional[str] = None


class LoginRequest(BaseModel):
    username_or_email: str
    password: str
    cf_turnstile_response: Optional[str] = None
