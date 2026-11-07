from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Integer, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column
from shared.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "admin"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, receipt, plan, test
    target_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SchoolDirectory(Base):
    __tablename__ = "schools"
    __table_args__ = {"schema": "admin"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
