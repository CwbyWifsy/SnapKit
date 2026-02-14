"""SQLAlchemy ORM models."""

from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class InstalledApp(Base):
    __tablename__ = "installed_apps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    publisher: Mapped[str | None] = mapped_column(String(255), default=None)
    install_location: Mapped[str | None] = mapped_column(Text, default=None)
    version: Mapped[str | None] = mapped_column(String(100), default=None)
    registry_key: Mapped[str | None] = mapped_column(Text, default=None)
    tags: Mapped[str | None] = mapped_column(Text, default=None)
    scanned_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    pinned: Mapped["PinnedApp | None"] = relationship(back_populates="installed_app")

    def __repr__(self) -> str:
        return f"<InstalledApp(id={self.id}, name={self.name!r})>"


class PinnedApp(Base):
    __tablename__ = "pinned_apps"

    id: Mapped[int] = mapped_column(primary_key=True)
    installed_app_id: Mapped[int] = mapped_column(ForeignKey("installed_apps.id"))
    launch_command: Mapped[str | None] = mapped_column(Text, default=None)
    tags: Mapped[str | None] = mapped_column(Text, default=None)
    pinned_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    installed_app: Mapped[InstalledApp] = relationship(back_populates="pinned")

    def __repr__(self) -> str:
        return f"<PinnedApp(id={self.id}, app={self.installed_app_id})>"


class NotInstalledApp(Base):
    __tablename__ = "not_installed_apps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    download_url: Mapped[str | None] = mapped_column(Text, default=None)
    tags: Mapped[str | None] = mapped_column(Text, default=None)
    added_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<NotInstalledApp(id={self.id}, name={self.name!r})>"


class ResourceItem(Base):
    __tablename__ = "resource_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(String(50))  # "file", "folder", "url"
    tags: Mapped[str | None] = mapped_column(Text, default=None)
    added_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<ResourceItem(id={self.id}, name={self.name!r})>"
