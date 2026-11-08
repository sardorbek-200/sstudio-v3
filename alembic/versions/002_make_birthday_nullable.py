"""make birthday nullable in auth.users

Revision ID: 002
Revises: 001
Create Date: 2026-11-08 20:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'birthday', existing_type=sa.Date(), nullable=True, schema='auth')


def downgrade() -> None:
    op.alter_column('users', 'birthday', existing_type=sa.Date(), nullable=False, schema='auth')
