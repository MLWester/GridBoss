"""add soft delete fields to leagues"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20250921_0002"
down_revision = "20250921_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leagues",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "leagues",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leagues", "deleted_at")
    op.drop_column("leagues", "is_deleted")
