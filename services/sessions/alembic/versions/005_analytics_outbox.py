from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: str | None = "004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_outbox",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="sessions",
    )
    op.create_index(
        "ix_analytics_outbox_created_at",
        "analytics_outbox",
        ["created_at"],
        schema="sessions",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analytics_outbox_created_at",
        table_name="analytics_outbox",
        schema="sessions",
    )
    op.drop_table("analytics_outbox", schema="sessions")
