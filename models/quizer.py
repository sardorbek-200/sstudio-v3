from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.database import Base


class Test(Base):
    __tablename__ = "tests"
    __table_args__ = {"schema": "quizer"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Test turlari: official (rasmiy), practice (mashq), secret (maxfiy PIN-kodli)
    test_type: Mapped[str] = mapped_column(String(50), default="practice", nullable=False)
    pin_code: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)  # 4 xonali PIN
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=30)  # Vaqt me'yori

    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    questions: Mapped[list["Question"]] = relationship("Question", back_populates="test", cascade="all, delete-orphan")
    results: Mapped[list["TestResult"]] = relationship("TestResult", back_populates="test", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "quizer"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quizer.tests.id", ondelete="CASCADE"), nullable=False)
    
    # Savol turi: single, multiple, open_ai, numeric, matching
    question_type: Mapped[str] = mapped_column(String(50), default="single", nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Variantlar va to'g'ri javoblar JSON matn ko'rinishida
    options_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correct_answer_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    points: Mapped[float] = mapped_column(Float, default=1.0)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    test: Mapped["Test"] = relationship("Test", back_populates="questions")


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = {"schema": "quizer"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quizer.tests.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)

    score: Mapped[float] = mapped_column(Float, default=0.0)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    test: Mapped["Test"] = relationship("Test", back_populates="results")


class AntiCheatLog(Base):
    __tablename__ = "anti_cheat_logs"
    __table_args__ = {"schema": "quizer"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # tab_switched, copy_paste, blurred
    warning_count: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
