from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.database import Base


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = {"schema": "shop"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), unique=True, nullable=False)
    scoin_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    frozen_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class SCoinTransaction(Base):
    __tablename__ = "scoin_transactions"
    __table_args__ = {"schema": "shop"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sender_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True)
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    fee_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 1% P2P transfer fee
    tx_type: Mapped[str] = mapped_column(String(50), nullable=False)  # p2p_transfer, wheel_win, plan_purchase, receipt_topup
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    __table_args__ = {"schema": "shop"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # pro, vip, teacher
    price_scoin: Mapped[float] = mapped_column(Float, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    ai_question_quota: Mapped[int] = mapped_column(Integer, default=50)
    test_publish_quota: Mapped[int] = mapped_column(Integer, default=20)
    features_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"
    __table_args__ = {"schema": "shop"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    amount_uzs: Mapped[float] = mapped_column(Float, nullable=False)
    scoin_requested: Mapped[float] = mapped_column(Float, nullable=False)
    receipt_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending, approved, rejected
    ai_precheck_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class WheelSpinHistory(Base):
    __tablename__ = "wheel_spin_history"
    __table_args__ = {"schema": "shop"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    prize_type: Mapped[str] = mapped_column(String(50), nullable=False)  # scoin, xp, badge, empty
    prize_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
