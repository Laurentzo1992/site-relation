"""remove 'autre' from the gender enum

Postgres has no ALTER TYPE ... DROP VALUE, so this recreates the `gender`
enum type without "autre" and swaps both columns that use it (users.gender,
ads.looking_for_gender) over to the new type.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Refuse to proceed if any row still uses the value being removed,
    # rather than silently losing data through the USING cast below.
    stale = bind.execute(
        sa.text(
            "SELECT count(*) FROM ("
            "  SELECT 1 FROM users WHERE gender = 'autre'"
            "  UNION ALL"
            "  SELECT 1 FROM ads WHERE looking_for_gender = 'autre'"
            ") t"
        )
    ).scalar()
    if stale:
        raise RuntimeError(
            f"{stale} row(s) still use gender='autre'; reassign them before running this migration."
        )

    op.execute("ALTER TYPE gender RENAME TO gender_old")
    op.execute("CREATE TYPE gender AS ENUM ('homme', 'femme')")
    op.execute("ALTER TABLE users ALTER COLUMN gender TYPE gender USING gender::text::gender")
    op.execute(
        "ALTER TABLE ads ALTER COLUMN looking_for_gender TYPE gender USING looking_for_gender::text::gender"
    )
    op.execute("DROP TYPE gender_old")


def downgrade() -> None:
    op.execute("ALTER TYPE gender RENAME TO gender_new")
    op.execute("CREATE TYPE gender AS ENUM ('homme', 'femme', 'autre')")
    op.execute("ALTER TABLE users ALTER COLUMN gender TYPE gender USING gender::text::gender")
    op.execute(
        "ALTER TABLE ads ALTER COLUMN looking_for_gender TYPE gender USING looking_for_gender::text::gender"
    )
    op.execute("DROP TYPE gender_new")
