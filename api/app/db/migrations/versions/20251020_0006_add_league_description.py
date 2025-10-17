"""Add league description column."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251020_0006_add_league_description"
down_revision: str | None = "20251011_0005_add_founder_flag"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:  # pragma: no cover - migration script
    op.add_column("leagues", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:  # pragma: no cover - migration script
    op.drop_column("leagues", "description")
