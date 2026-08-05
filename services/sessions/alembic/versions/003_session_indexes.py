from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_sessions_user_id",
        "sessions",
        ["user_id"],
        schema="sessions",
    )
    op.create_index(
        "ix_sessions_user_pack_status",
        "sessions",
        ["user_id", "pack_version_id", "status"],
        schema="sessions",
    )
    op.create_index(
        "ix_attempts_session_id",
        "attempts",
        ["session_id"],
        schema="sessions",
    )


def downgrade() -> None:
    op.drop_index("ix_attempts_session_id", table_name="attempts", schema="sessions")
    op.drop_index("ix_sessions_user_pack_status", table_name="sessions", schema="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions", schema="sessions")
