"""add plan grace columns"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20250924_0004_plan_grace"
down_revision: str | None = "20250924_0003_stripe_events"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("billing_accounts", sa.Column("plan_grace_plan", sa.String(), nullable=True))
    op.add_column(
        "billing_accounts",
        sa.Column("plan_grace_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("billing_accounts", "plan_grace_expires_at")
    op.drop_column("billing_accounts", "plan_grace_plan")
