\
\
\
\
\
   

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("topic_assess_scores", schema="analytics")


def downgrade() -> None:
    op.create_table(
        "topic_assess_scores",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", sa.String(length=128), nullable=False),
        sa.Column("best_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "session_id", "topic_id"),
        schema="analytics",
    )
