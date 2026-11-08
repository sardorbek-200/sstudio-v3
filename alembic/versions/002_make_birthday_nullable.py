"""make birthday nullable in auth.users

Revision ID: 002_birthday_nullable
Revises: 001_initial
Create Date: 2026-11-08 20:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002_birthday_nullable'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'birthday', existing_type=sa.Date(), nullable=True, schema='auth')


def downgrade() -> None:
    op.alter_column('users', 'birthday', existing_type=sa.Date(), nullable=False, schema='auth')
