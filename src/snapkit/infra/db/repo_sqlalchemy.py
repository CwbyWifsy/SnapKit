from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Engine, or_

from snapkit.core.entities import UiItem
from snapkit.db import get_session
from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp, ResourceItem


class SqlAlchemyToolboxRepository:
    def __init__(self, engine: Engine):
        self._engine = engine
        self._session_factory: Callable = lambda: get_session(self._engine)

    def list_installed(
        self, search: str = "", limit: int = 300, pinned_filter: str = "all"
    ) -> list[UiItem]:
        session = self._session_factory()
        try:
            query = session.query(InstalledApp)
            if search:
                query = query.filter(
                    or_(
                        InstalledApp.name.ilike(f"%{search}%"),
                        InstalledApp.custom_name.ilike(f"%{search}%"),
                    )
                )

            apps = query.order_by(InstalledApp.name).limit(limit).all()
            pin_pairs = session.query(PinnedApp.id, PinnedApp.installed_app_id).all()
            pin_map = {installed_id: pin_id for pin_id, installed_id in pin_pairs}

            if pinned_filter == "pinned":
                apps = [app for app in apps if app.id in pin_map]
            elif pinned_filter == "unpinned":
                apps = [app for app in apps if app.id not in pin_map]

            return [
                UiItem(
                    item_id=app.id,
                    title=app.custom_name or app.name,
                    subtitle=app.publisher or app.version or "Unknown Publisher",
                    badge="LOCAL APP",
                    kind="local",
                    install_location=app.install_location,
                    uninstall_command=app.uninstall_command,
                    icon_path=app.custom_icon_path or _clean_display_icon(app.display_icon),
                    is_pinned=app.id in pin_map,
                )
                for app in apps
            ]
        finally:
            session.close()

    def list_pinned(self, search: str = "", limit: int = 300) -> list[UiItem]:
        session = self._session_factory()
        try:
            query = session.query(PinnedApp)
            pins = query.order_by(PinnedApp.pinned_at.desc()).limit(limit).all()
            if search:
                lowered = search.lower()
                pins = [
                    p
                    for p in pins
                    if lowered in (p.installed_app.custom_name or p.installed_app.name).lower()
                ]

            return [
                UiItem(
                    item_id=pin.id,
                    title=pin.installed_app.custom_name or pin.installed_app.name,
                    subtitle=pin.installed_app.publisher or "Pinned App",
                    badge="PINNED",
                    kind="pinned",
                    install_location=pin.installed_app.install_location,
                    launch_command=pin.launch_command,
                    uninstall_command=pin.installed_app.uninstall_command,
                    icon_path=pin.installed_app.custom_icon_path
                    or _clean_display_icon(pin.installed_app.display_icon),
                    linked_app_id=pin.installed_app.id,
                    is_pinned=True,
                )
                for pin in pins
            ]
        finally:
            session.close()

    def list_not_installed(self, search: str = "", limit: int = 300) -> list[UiItem]:
        session = self._session_factory()
        try:
            query = session.query(NotInstalledApp)
            if search:
                query = query.filter(NotInstalledApp.name.ilike(f"%{search}%"))

            installed_names: set[str] = set()
            for name, custom_name in session.query(InstalledApp.name, InstalledApp.custom_name).all():
                if name:
                    installed_names.add(name.strip().lower())
                if custom_name:
                    installed_names.add(custom_name.strip().lower())

            apps = query.order_by(NotInstalledApp.added_at.desc()).all()
            apps = [app for app in apps if app.name.strip().lower() not in installed_names][:limit]
            return [
                UiItem(
                    item_id=app.id,
                    title=app.name,
                    subtitle=app.description or "收藏中未安装",
                    badge="WISHLIST",
                    kind="wish",
                    download_url=app.download_url,
                )
                for app in apps
            ]
        finally:
            session.close()

    def list_resources(
        self, resource_type: str, search: str = "", limit: int = 300
    ) -> list[UiItem]:
        session = self._session_factory()
        try:
            query = session.query(ResourceItem).filter_by(resource_type=resource_type)
            if search:
                query = query.filter(ResourceItem.name.ilike(f"%{search}%"))

            items = query.order_by(ResourceItem.added_at.desc()).limit(limit).all()
            return [
                UiItem(
                    item_id=item.id,
                    title=item.name,
                    subtitle=_shorten(item.path),
                    badge="WEBSITE" if item.resource_type == "url" else "RESOURCE",
                    kind="resource",
                    path=item.path,
                    resource_type=item.resource_type,
                    icon_path=item.path if item.resource_type != "url" else None,
                )
                for item in items
            ]
        finally:
            session.close()


def _shorten(value: str, max_len: int = 48) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 3]}..."


def _clean_display_icon(display_icon: str | None) -> str | None:
    """Normalize registry DisplayIcon value into a plain filesystem path."""
    if not display_icon:
        return None

    value = display_icon.strip().strip('"').strip()
    if "," in value:
        value = value.split(",", 1)[0].strip().strip('"')
    return value or None
