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
    op.add_column(
        "sessions",
        sa.Column(
            "completed_step_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema="sessions",
    )
    op.alter_column(
        "sessions",
        "completed_step_ids",
        server_default=None,
        schema="sessions",
    )


def downgrade() -> None:
    op.drop_column("sessions", "completed_step_ids", schema="sessions")
