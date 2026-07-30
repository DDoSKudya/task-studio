from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pack_versions",
        sa.Column("object_key", sa.Text(), nullable=True),
        schema="catalog",
    )


def downgrade() -> None:
    op.drop_column("pack_versions", "object_key", schema="catalog")
