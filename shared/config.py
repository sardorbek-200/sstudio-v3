from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = Field(default="dev_secret_key_change_in_production_32chars")
    BASE_DOMAIN: str = "sstudio.uz"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/sstudio_v3"

    # Gemini Dual Keys
    GEMINI_API_KEY_1: Optional[str] = None
    GEMINI_API_KEY_2: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None
    TELEGRAM_ADMIN_ID: Optional[int] = None

    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: str = "https://auth.sstudio.uz/github/callback"

    # Cloudflare Turnstile
    CLOUDFLARE_TURNSTILE_SITE_KEY: Optional[str] = None
    CLOUDFLARE_TURNSTILE_SECRET_KEY: Optional[str] = None


settings = Settings()
