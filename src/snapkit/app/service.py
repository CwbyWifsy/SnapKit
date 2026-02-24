from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from sqlalchemy import Engine, or_

from snapkit.app.usecases.list_apps import list_items
from snapkit.app.usecases.open_item import activate_item, open_item_folder, uninstall_item
from snapkit.app.usecases.scan_apps import scan_installed_apps
from snapkit.core.entities import UiItem, ViewId
from snapkit.core.protocols import ToolboxRepository
from snapkit.db import get_session
from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp, ResourceItem


class SnapKitService:
    def __init__(self, repo: ToolboxRepository, engine: Engine):
        self._repo = repo
        self._engine = engine
        self._item_index: dict[int, UiItem] = {}

    def load_view(
        self, view_id: ViewId, search: str = "", local_filter: str = "all"
    ) -> tuple[str, str, list[UiItem]]:
        title, subtitle, items = list_items(
            self._repo,
            view_id=view_id,
            search=search,
            local_filter=local_filter,
        )
        self._item_index = {item.item_id: item for item in items}
        return title, subtitle, items

    def activate_item(self, item_id: int) -> tuple[bool, str]:
        item = self._item_index.get(item_id)
        if not item:
            return False, "项目不存在或已过期，请刷新后重试"
        return activate_item(item)

    def scan_apps(self) -> tuple[bool, str]:
        found, added = scan_installed_apps(self._engine)
        if found == 0:
            return False, "未扫描到应用，请确认在 Windows 系统中运行并有注册表读取权限"
        return True, f"扫描完成：发现 {found} 个应用，新增 {added} 个"

    def perform_action(self, item_id: int, action: str) -> tuple[bool, str]:
        item = self._item_index.get(item_id)
        if not item:
            return False, "项目不存在或已过期，请刷新后重试"

        if action == "launch":
            return activate_item(item)
        if action == "admin_launch":
            return activate_item(item, as_admin=True)
        if action == "open_folder":
            return open_item_folder(item)
        if action == "uninstall":
            return uninstall_item(item)
        if action == "pin":
            return self._pin_item(item)
        if action == "unpin":
            return self._unpin_item(item)
        if action == "delete":
            return self._delete_item(item)

        return False, f"不支持的操作: {action}"

    def rename_item(self, item_id: int, new_name: str) -> tuple[bool, str]:
        item = self._item_index.get(item_id)
        if not item:
            return False, "项目不存在或已过期，请刷新后重试"

        name = new_name.strip()
        if not name:
            return False, "名称不能为空"

        session = get_session(self._engine)
        try:
            if item.kind == "local":
                app = session.get(InstalledApp, item.item_id)
                if not app:
                    return False, "项目不存在"
                app.custom_name = name
            elif item.kind == "pinned":
                pin = session.get(PinnedApp, item.item_id)
                if not pin or not pin.installed_app:
                    return False, "项目不存在"
                pin.installed_app.custom_name = name
            elif item.kind == "wish":
                wish = session.get(NotInstalledApp, item.item_id)
                if not wish:
                    return False, "项目不存在"
                wish.name = name
            elif item.kind == "resource":
                res = session.get(ResourceItem, item.item_id)
                if not res:
                    return False, "项目不存在"
                res.name = name
            else:
                return False, "该类型不支持重命名"

            session.commit()
            self._item_index[item_id] = replace(item, title=name)
            return True, f"已重命名为: {name}"
        finally:
            session.close()

    def set_custom_icon(self, item_id: int, icon_path: str) -> tuple[bool, str]:
        item = self._item_index.get(item_id)
        if not item:
            return False, "项目不存在或已过期，请刷新后重试"

        path = Path(icon_path)
        if not path.exists():
            return False, "图标文件不存在"
        if path.suffix.lower() != ".exe":
            return False, "请选择 exe 文件以提取图标"

        session = get_session(self._engine)
        try:
            if item.kind == "local":
                app = session.get(InstalledApp, item.item_id)
                if not app:
                    return False, "项目不存在"
                app.custom_icon_path = str(path)
            elif item.kind == "pinned":
                pin = session.get(PinnedApp, item.item_id)
                if not pin or not pin.installed_app:
                    return False, "项目不存在"
                pin.installed_app.custom_icon_path = str(path)
            else:
                return False, "该类型不支持自定义图标"

            session.commit()
            self._item_index[item_id] = replace(item, icon_path=str(path))
            return True, f"已设置自定义图标: {item.title}"
        finally:
            session.close()

    def quick_add(
        self,
        item_type: str,
        name: str,
        target: str = "",
        note: str = "",
        icon_path: str = "",
        source_mode: str = "local",
    ) -> tuple[bool, str]:
        normalized_name = name.strip()
        normalized_target = target.strip()
        normalized_note = note.strip()
        normalized_icon = icon_path.strip()
        normalized_mode = source_mode.strip().lower() or "local"

        session = get_session(self._engine)
        try:
            if item_type == "local_app":
                return self._quick_add_local_app(
                    session,
                    name=normalized_name,
                    target=normalized_target,
                    icon_path=normalized_icon,
                )
            if item_type == "wish":
                return self._quick_add_wish(
                    session,
                    name=normalized_name,
                    target=normalized_target,
                    note=normalized_note,
                )
            if item_type == "website":
                return self._quick_add_website(
                    session,
                    name=normalized_name,
                    target=normalized_target,
                    note=normalized_note,
                )

            resource_map = {
                "document": "document",
                "image": "image",
                "video": "video",
            }
            resource_type = resource_map.get(item_type)
            if not resource_type:
                return False, f"不支持的快速添加类型: {item_type}"
            if not normalized_target:
                return False, "请填写路径或链接"

            if normalized_mode == "network":
                normalized_target = _normalize_web_url(normalized_target)
                if not _is_web_url(normalized_target):
                    return False, "网络资源必须是 http/https 链接"
                final_target = normalized_target
            else:
                local_path = _to_existing_path(normalized_target)
                if not local_path:
                    return False, "本地资源路径不存在"
                final_target = str(local_path)

            return self._upsert_resource(
                session=session,
                resource_type=resource_type,
                name=normalized_name,
                target=final_target,
                note=normalized_note,
                ok_prefix="资源",
            )
        finally:
            session.close()

    def _delete_item(self, item: UiItem) -> tuple[bool, str]:
        session = get_session(self._engine)
        try:
            if item.kind == "local":
                app = session.get(InstalledApp, item.item_id)
                if not app:
                    return False, "项目不存在"
                session.query(PinnedApp).filter_by(installed_app_id=app.id).delete()
                session.delete(app)
            elif item.kind == "pinned":
                pin = session.get(PinnedApp, item.item_id)
                if not pin:
                    return False, "项目不存在"
                session.delete(pin)
            elif item.kind == "wish":
                wish = session.get(NotInstalledApp, item.item_id)
                if not wish:
                    return False, "项目不存在"
                session.delete(wish)
            elif item.kind == "resource":
                res = session.get(ResourceItem, item.item_id)
                if not res:
                    return False, "项目不存在"
                session.delete(res)
            else:
                return False, "该类型不支持删除"

            session.commit()
            self._item_index.pop(item.item_id, None)
            return True, f"已删除: {item.title}"
        finally:
            session.close()

    def _pin_item(self, item: UiItem) -> tuple[bool, str]:
        if item.kind not in {"local", "pinned"}:
            return False, "该类型不支持收藏"

        if item.kind == "pinned":
            return False, f"{item.title} 已在收藏中"

        session = get_session(self._engine)
        try:
            app = session.get(InstalledApp, item.item_id)
            if not app:
                return False, "项目不存在"

            existing = session.query(PinnedApp).filter_by(installed_app_id=app.id).first()
            if existing:
                return False, f"{item.title} 已在收藏中"

            session.add(PinnedApp(installed_app_id=app.id))
            wish_name = (app.custom_name or app.name or "").strip()
            if wish_name:
                session.query(NotInstalledApp).filter(NotInstalledApp.name.ilike(wish_name)).delete(
                    synchronize_session=False
                )
            session.commit()
            return True, f"已收藏: {item.title}"
        finally:
            session.close()

    def _unpin_item(self, item: UiItem) -> tuple[bool, str]:
        if item.kind not in {"local", "pinned"}:
            return False, "该类型不支持取消收藏"

        session = get_session(self._engine)
        try:
            if item.kind == "pinned":
                entry = session.get(PinnedApp, item.item_id)
            else:
                entry = session.query(PinnedApp).filter_by(installed_app_id=item.item_id).first()

            if not entry:
                return False, f"{item.title} 不在收藏中"

            session.delete(entry)
            session.commit()
            return True, f"已取消收藏: {item.title}"
        finally:
            session.close()

    def _quick_add_wish(
        self,
        session,
        name: str,
        target: str,
        note: str,
    ) -> tuple[bool, str]:
        title = name or _guess_name_from_target(target)
        if not title:
            return False, "请填写软件名称"

        installed = (
            session.query(InstalledApp)
            .filter(
                or_(
                    InstalledApp.name.ilike(title),
                    InstalledApp.custom_name.ilike(title),
                )
            )
            .first()
        )
        if installed:
            existing_pin = session.query(PinnedApp).filter_by(installed_app_id=installed.id).first()
            if existing_pin:
                return True, f"已安装且已收藏: {installed.custom_name or installed.name}"
            session.add(PinnedApp(installed_app_id=installed.id))
            session.query(NotInstalledApp).filter(NotInstalledApp.name.ilike(title)).delete(
                synchronize_session=False
            )
            session.commit()
            return True, f"检测到已安装，已加入收藏: {installed.custom_name or installed.name}"

        wish = session.query(NotInstalledApp).filter(NotInstalledApp.name.ilike(title)).first()
        if wish:
            if note:
                wish.description = note
            if target:
                wish.download_url = target
            session.commit()
            return True, f"已更新待安装: {wish.name}"

        session.add(
            NotInstalledApp(
                name=title,
                description=note or "收藏中未安装",
                download_url=target or None,
            )
        )
        session.commit()
        return True, f"已添加待安装: {title}"

    def _quick_add_local_app(
        self,
        session,
        name: str,
        target: str,
        icon_path: str,
    ) -> tuple[bool, str]:
        exe_path = _to_existing_path(target)
        if not exe_path:
            return False, "请选择有效的本地可执行文件"
        if exe_path.suffix.lower() not in {".exe", ".lnk", ".bat", ".cmd"}:
            return False, "本地应用只支持 exe/lnk/bat/cmd"

        icon_candidate = exe_path
        if icon_path:
            picked_icon = _to_existing_path(icon_path)
            if not picked_icon:
                return False, "图标文件不存在"
            icon_candidate = picked_icon

        title = name or exe_path.stem
        manual_key = f"MANUAL::{str(exe_path).lower()}"
        existing = (
            session.query(InstalledApp)
            .filter(
                or_(
                    InstalledApp.registry_key == manual_key,
                    InstalledApp.install_location.ilike(str(exe_path)),
                )
            )
            .first()
        )
        if existing:
            existing.name = title
            existing.custom_name = title
            existing.publisher = existing.publisher or "Manual Added"
            existing.install_location = str(exe_path)
            existing.custom_icon_path = str(icon_candidate)
            existing.display_icon = str(icon_candidate)
            existing.registry_key = existing.registry_key or manual_key
            session.commit()
            return True, f"已更新本地应用: {title}"

        session.add(
            InstalledApp(
                name=title,
                custom_name=title,
                publisher="Manual Added",
                install_location=str(exe_path),
                custom_icon_path=str(icon_candidate),
                display_icon=str(icon_candidate),
                registry_key=manual_key,
            )
        )
        session.commit()
        return True, f"已添加本地应用: {title}"

    def _quick_add_website(
        self,
        session,
        name: str,
        target: str,
        note: str,
    ) -> tuple[bool, str]:
        normalized_target = _normalize_web_url(target)
        if not normalized_target:
            return False, "请填写网址"
        if not _is_web_url(normalized_target):
            return False, "网址必须是 http/https"

        return self._upsert_resource(
            session=session,
            resource_type="url",
            name=name,
            target=normalized_target,
            note=note,
            ok_prefix="网站",
        )

    def _upsert_resource(
        self,
        session,
        resource_type: str,
        name: str,
        target: str,
        note: str,
        ok_prefix: str,
    ) -> tuple[bool, str]:
        title = name or _guess_name_from_target(target)
        existing = (
            session.query(ResourceItem)
            .filter_by(resource_type=resource_type, path=target)
            .first()
        )
        if existing:
            if title and existing.name != title:
                existing.name = title
            if note:
                existing.tags = note
            session.commit()
            return True, f"{ok_prefix}已存在: {existing.name}"

        session.add(
            ResourceItem(
                name=title,
                path=target,
                resource_type=resource_type,
                tags=note or None,
            )
        )
        session.commit()
        return True, f"已添加{ok_prefix}: {title}"


def _guess_name_from_target(target: str) -> str:
    raw = target.strip().strip('"')
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        host = raw.split("//", 1)[1]
        return host.split("/", 1)[0]
    return Path(raw).stem or Path(raw).name


def _to_existing_path(value: str) -> Path | None:
    raw = value.strip().strip('"')
    if not raw:
        return None
    path = Path(raw)
    if path.exists():
        return path
    return None


def _is_web_url(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _normalize_web_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return raw
    if "://" not in raw and "." in raw:
        return f"https://{raw}"
    return raw
