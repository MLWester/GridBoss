"""add founder flag to users.

Revision ID: 20251011_0005_add_founder_flag
Revises: 20250924_0004_plan_grace
Create Date: 2025-10-11 21:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251011_0005_add_founder_flag"
down_revision: str = "20250924_0004_plan_grace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_founder",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute("UPDATE users SET is_founder = false WHERE is_founder IS NULL")
    op.alter_column("users", "is_founder", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_founder")

