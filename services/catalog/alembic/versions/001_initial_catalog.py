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
    op.execute("CREATE SCHEMA IF NOT EXISTS catalog")
    op.create_table(
        "packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "slug", name="uq_packs_owner_slug"),
        schema="catalog",
    )
    op.create_table(
        "pack_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("disk_path", sa.Text(), nullable=False),
        sa.Column("import_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pack_id"], ["catalog.packs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pack_id", "version", name="uq_pack_versions_pack_version"),
        schema="catalog",
    )
    op.create_table(
        "user_packs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["pack_id"], ["catalog.packs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pack_version_id"],
            ["catalog.pack_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "pack_id"),
        schema="catalog",
    )


def downgrade() -> None:
    op.drop_table("user_packs", schema="catalog")
    op.drop_table("pack_versions", schema="catalog")
    op.drop_table("packs", schema="catalog")
    op.execute("DROP SCHEMA IF EXISTS catalog")
