"""initial sessions schema

Revision ID: 001
Revises:
Create Date: 2026-07-11
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
    op.execute("CREATE SCHEMA IF NOT EXISTS sessions")
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("current_topic_id", sa.String(length=128), nullable=False),
        sa.Column("current_phase", sa.String(length=16), nullable=False),
        sa.Column("current_step_id", sa.String(length=128), nullable=False),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="sessions",
    )
    op.create_table(
        "attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", sa.String(length=128), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("step_id", sa.String(length=128), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("submission", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="sessions",
    )
    op.create_table(
        "phase_progress",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", sa.String(length=128), nullable=False),
        sa.Column("study_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("study_skipped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "practice_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "assess_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("assess_best_score", sa.Numeric(5, 2), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "topic_id"),
        schema="sessions",
    )
    op.create_table(
        "course_assess_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
        schema="sessions",
    )


def downgrade() -> None:
    op.drop_table("course_assess_sessions", schema="sessions")
    op.drop_table("phase_progress", schema="sessions")
    op.drop_table("attempts", schema="sessions")
    op.drop_table("sessions", schema="sessions")
    op.execute("DROP SCHEMA IF EXISTS sessions")
