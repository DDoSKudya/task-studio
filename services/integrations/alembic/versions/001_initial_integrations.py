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

revision: str = "001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS integrations")
    op.create_table(
        "import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_id", sa.String(length=32), nullable=False),
        sa.Column("external_course_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("pack_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="integrations",
    )
    op.create_index(
        "ix_import_jobs_user_platform_course",
        "import_jobs",
        ["user_id", "platform_id", "external_course_id"],
        schema="integrations",
    )
    op.create_table(
        "external_course_cache",
        sa.Column("platform_id", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("platform_id", "external_id", "user_id"),
        schema="integrations",
    )


def downgrade() -> None:
    op.drop_table("external_course_cache", schema="integrations")
    op.drop_index(
        "ix_import_jobs_user_platform_course",
        table_name="import_jobs",
        schema="integrations",
    )
    op.drop_table("import_jobs", schema="integrations")
    op.execute("DROP SCHEMA IF EXISTS integrations")
