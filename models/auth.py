from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey,
    Index, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    # Asosiy
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    # Shaxsiy ma'lumotlar
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    father_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)

    # Joylashuv
    location_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Ta'lim & Maktab
    school_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    school_normalized: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    school_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # school, university, not_studying

    # Profil
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Aloqa
    tel_number: Mapped[Optional[str]] = mapped_column(String(30), unique=True, nullable=True)
    gmail: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True, index=True)

    # Social tarmoqlar & Coding usernames
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    github_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    codeforces_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    robocontest_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    leetcode_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    atcoder_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    x_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    youtube_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Shaxsiy saytlar
    web1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    web2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    web3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Tasdiqlashlar
    gmail_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    github_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Tarif / Status
    status: Mapped[str] = mapped_column(String(50), default="freemium", nullable=False)

    # Tizim
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    oauth_connections: Mapped[list["OAuthConnection"]] = relationship(
        "OAuthConnection", back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    """PostgreSQL asosidagi sessiyalar (Redis o'rniga)"""
    __tablename__ = "sessions"
    __table_args__ = (
        Index("idx_sessions_token", "token_hash"),
        Index("idx_sessions_expires", "expires_at"),
        {"schema": "auth"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Masalan: "Chrome on Windows"
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class OAuthConnection(Base):
    __tablename__ = "oauth_connections"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        {"schema": "auth"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, github, telegram
    provider_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="oauth_connections")
