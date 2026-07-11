from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Pack(Base):
    __tablename__ = "packs"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "slug", name="uq_packs_owner_slug"),
        {"schema": "catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    versions: Mapped[list[PackVersion]] = relationship(
        back_populates="pack",
        cascade="all, delete-orphan",
    )
    installations: Mapped[list[UserPack]] = relationship(
        back_populates="pack",
        cascade="all, delete-orphan",
    )


class PackVersion(Base):
    __tablename__ = "pack_versions"
    __table_args__ = (
        UniqueConstraint("pack_id", "version", name="uq_pack_versions_pack_version"),
        {"schema": "catalog"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.packs.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    disk_path: Mapped[str] = mapped_column(Text, nullable=False)
    import_report: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    pack: Mapped[Pack] = relationship(back_populates="versions")
    installations: Mapped[list[UserPack]] = relationship(back_populates="pack_version")


class UserPack(Base):
    __tablename__ = "user_packs"
    __table_args__ = {"schema": "catalog"}

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.packs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pack_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.pack_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pack: Mapped[Pack] = relationship(back_populates="installations")
    pack_version: Mapped[PackVersion] = relationship(back_populates="installations")
