"""add whatsapp flag, tighten phone column to E.164 length

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("whatsapp", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("users", "phone", type_=sa.String(20), existing_type=sa.String(50))


def downgrade() -> None:
    op.alter_column("users", "phone", type_=sa.String(50), existing_type=sa.String(20))
    op.drop_column("users", "whatsapp")
