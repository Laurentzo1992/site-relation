"""add ligdicash payment fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("provider_token", sa.String(1000), nullable=True))
    op.add_column("payments", sa.Column("checkout_url", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "checkout_url")
    op.drop_column("payments", "provider_token")
