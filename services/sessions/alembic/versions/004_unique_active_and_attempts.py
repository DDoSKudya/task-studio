from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_sessions_active_user_pack",
        "sessions",
        ["user_id", "pack_version_id"],
        unique=True,
        schema="sessions",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_unique_constraint(
        "uq_attempts_session_topic_phase_step_number",
        "attempts",
        ["session_id", "topic_id", "phase", "step_id", "attempt_number"],
        schema="sessions",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_attempts_session_topic_phase_step_number",
        "attempts",
        schema="sessions",
        type_="unique",
    )
    op.drop_index(
        "uq_sessions_active_user_pack",
        table_name="sessions",
        schema="sessions",
    )
