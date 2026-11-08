"""Initial ecosystem schemas and tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-11-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Schemalarni yaratish
    op.execute("CREATE SCHEMA IF NOT EXISTS auth;")
    op.execute("CREATE SCHEMA IF NOT EXISTS quizer;")
    op.execute("CREATE SCHEMA IF NOT EXISTS shop;")
    op.execute("CREATE SCHEMA IF NOT EXISTS admin;")

    # 2. auth.users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("surname", sa.String(length=100), nullable=False),
        sa.Column("father_name", sa.String(length=100), nullable=True),
        sa.Column("birthday", sa.Date(), nullable=False),
        sa.Column("location_region", sa.String(length=100), nullable=True),
        sa.Column("location_city", sa.String(length=100), nullable=True),
        sa.Column("school_raw", sa.Text(), nullable=True),
        sa.Column("school_normalized", sa.String(length=255), nullable=True),
        sa.Column("school_type", sa.String(length=50), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("tel_number", sa.String(length=30), nullable=True),
        sa.Column("gmail", sa.String(length=255), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_username", sa.String(length=100), nullable=True),
        sa.Column("github_username", sa.String(length=100), nullable=True),
        sa.Column("codeforces_username", sa.String(length=100), nullable=True),
        sa.Column("robocontest_username", sa.String(length=100), nullable=True),
        sa.Column("leetcode_username", sa.String(length=100), nullable=True),
        sa.Column("atcoder_username", sa.String(length=100), nullable=True),
        sa.Column("x_username", sa.String(length=100), nullable=True),
        sa.Column("youtube_username", sa.String(length=100), nullable=True),
        sa.Column("web1", sa.String(length=255), nullable=True),
        sa.Column("web2", sa.String(length=255), nullable=True),
        sa.Column("web3", sa.String(length=255), nullable=True),
        sa.Column("gmail_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("telegram_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("github_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="freemium", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_banned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("tel_number"),
        sa.UniqueConstraint("gmail"),
        sa.UniqueConstraint("telegram_id"),
        schema="auth"
    )
    op.create_index("ix_auth_users_username", "users", ["username"], unique=True, schema="auth")
    op.create_index("ix_auth_users_gmail", "users", ["gmail"], unique=True, schema="auth")
    op.create_index("ix_auth_users_school_norm", "users", ["school_normalized"], unique=False, schema="auth")

    # 3. auth.sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        schema="auth"
    )
    op.create_index("idx_sessions_token", "sessions", ["token_hash"], schema="auth")
    op.create_index("idx_sessions_expires", "sessions", ["expires_at"], schema="auth")

    # 4. auth.oauth_connections
    op.create_table(
        "oauth_connections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        schema="auth"
    )

    # 5. quizer.tests
    op.create_table(
        "tests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("test_type", sa.String(length=50), server_default="practice", nullable=False),
        sa.Column("pin_code", sa.String(length=4), nullable=True),
        sa.Column("time_limit_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="quizer"
    )

    # 6. quizer.questions
    op.create_table(
        "questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("test_id", sa.BigInteger(), nullable=False),
        sa.Column("question_type", sa.String(length=50), server_default="single", nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("correct_answer_json", sa.Text(), nullable=False),
        sa.Column("points", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["test_id"], ["quizer.tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="quizer"
    )

    # 7. quizer.test_results
    op.create_table(
        "test_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("test_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("xp_earned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["quizer.tests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="quizer"
    )

    # 8. quizer.anti_cheat_logs
    op.create_table(
        "anti_cheat_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("test_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("warning_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="quizer"
    )

    # 9. shop.wallets
    op.create_table(
        "wallets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("scoin_balance", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("frozen_balance", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        schema="shop"
    )

    # 10. shop.scoin_transactions
    op.create_table(
        "scoin_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=True),
        sa.Column("receiver_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("fee_amount", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("tx_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["receiver_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="shop"
    )

    # 11. shop.subscription_plans
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("price_scoin", sa.Float(), nullable=False),
        sa.Column("duration_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("ai_question_quota", sa.Integer(), server_default="50", nullable=False),
        sa.Column("test_publish_quota", sa.Integer(), server_default="20", nullable=False),
        sa.Column("features_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        schema="shop"
    )

    # 12. shop.payment_receipts
    op.create_table(
        "payment_receipts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount_uzs", sa.Float(), nullable=False),
        sa.Column("scoin_requested", sa.Float(), nullable=False),
        sa.Column("receipt_image_path", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("ai_precheck_data", sa.Text(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="shop"
    )

    # 13. shop.wheel_spin_history
    op.create_table(
        "wheel_spin_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("prize_type", sa.String(length=50), nullable=False),
        sa.Column("prize_amount", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="shop"
    )

    # 14. admin.audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("telegram_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="admin"
    )

    # 15. admin.schools
    op.create_table(
        "schools",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("school_name", sa.String(length=200), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="admin"
    )


def downgrade() -> None:
    op.drop_table("schools", schema="admin")
    op.drop_table("audit_logs", schema="admin")
    op.drop_table("wheel_spin_history", schema="shop")
    op.drop_table("payment_receipts", schema="shop")
    op.drop_table("subscription_plans", schema="shop")
    op.drop_table("scoin_transactions", schema="shop")
    op.drop_table("wallets", schema="shop")
    op.drop_table("anti_cheat_logs", schema="quizer")
    op.drop_table("test_results", schema="quizer")
    op.drop_table("questions", schema="quizer")
    op.drop_table("tests", schema="quizer")
    op.drop_table("oauth_connections", schema="auth")
    op.drop_table("sessions", schema="auth")
    op.drop_table("users", schema="auth")
    op.execute("DROP SCHEMA IF EXISTS admin CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS shop CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS quizer CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE;")
