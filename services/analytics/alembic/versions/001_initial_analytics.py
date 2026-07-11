"""initial analytics schema

Revision ID: 001
Revises:
Create Date: 2026-07-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    op.create_table(
        "processed_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
        schema="analytics",
    )
    op.create_table(
        "daily_user_progress",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("sessions_started", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("steps_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("user_id", "day"),
        schema="analytics",
    )
    op.create_table(
        "study_skip_counts",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("topic_id", sa.String(length=128), nullable=False),
        sa.Column("skip_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_skipped_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "session_id", "topic_id"),
        schema="analytics",
    )
    op.create_table(
        "topic_assess_scores",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", sa.String(length=128), nullable=False),
        sa.Column(
            "best_score",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "session_id", "topic_id"),
        schema="analytics",
    )
    op.create_table(
        "attempt_timeline",
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("topic_id", sa.String(length=128), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("step_id", sa.String(length=128), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("attempt_id"),
        schema="analytics",
    )
    op.create_index(
        "ix_attempt_timeline_user_created",
        "attempt_timeline",
        ["user_id", "created_at"],
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attempt_timeline_user_created",
        table_name="attempt_timeline",
        schema="analytics",
    )
    op.drop_table("attempt_timeline", schema="analytics")
    op.drop_table("topic_assess_scores", schema="analytics")
    op.drop_table("study_skip_counts", schema="analytics")
    op.drop_table("daily_user_progress", schema="analytics")
    op.drop_table("processed_events", schema="analytics")
    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
