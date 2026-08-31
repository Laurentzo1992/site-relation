"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: these enum types are created/dropped explicitly below via
# .create()/.drop() so that reusing the same type across two tables (e.g.
# "gender" on both users and ads) doesn't try to CREATE TYPE twice. Must use
# the postgresql-specific ENUM (not the generic sa.Enum) for create_type to
# actually be honored when the column is emitted as part of CREATE TABLE.
gender_enum = PGEnum("homme", "femme", "autre", name="gender", create_type=False)
ad_status_enum = PGEnum(
    "draft", "pending_payment", "published", "rejected", "archived", name="adstatus", create_type=False
)
connection_status_enum = PGEnum(
    "pending_payment", "pending_admin", "approved", "rejected", name="connectionstatus", create_type=False
)
payment_type_enum = PGEnum("ad_publication", "connection_request", name="paymenttype", create_type=False)
payment_status_enum = PGEnum("pending", "success", "failed", name="paymentstatus", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    gender_enum.create(bind, checkfirst=True)
    ad_status_enum.create(bind, checkfirst=True)
    connection_status_enum.create(bind, checkfirst=True)
    payment_type_enum.create(bind, checkfirst=True)
    payment_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("gender", gender_enum, nullable=False),
        sa.Column("birthdate", sa.Date(), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "ads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("looking_for_gender", gender_enum, nullable=False),
        sa.Column("min_age", sa.Integer(), nullable=True),
        sa.Column("max_age", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("status", ad_status_enum, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "connection_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ad_id", sa.Integer(), sa.ForeignKey("ads.id"), nullable=False),
        sa.Column("status", connection_status_enum, nullable=False, server_default="pending_payment"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", payment_type_enum, nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("status", payment_status_enum, nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(50), nullable=False, server_default="mock"),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("connection_requests")
    op.drop_table("ads")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    payment_status_enum.drop(bind, checkfirst=True)
    payment_type_enum.drop(bind, checkfirst=True)
    connection_status_enum.drop(bind, checkfirst=True)
    ad_status_enum.drop(bind, checkfirst=True)
    gender_enum.drop(bind, checkfirst=True)
