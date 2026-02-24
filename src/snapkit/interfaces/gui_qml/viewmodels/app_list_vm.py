from __future__ import annotations

from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, Signal, Slot

from snapkit.app.service import SnapKitService
from snapkit.interfaces.gui_qml.models.app_list_model import AppListModel


class AppListViewModel(QObject):
    pageTitleChanged = Signal()
    pageSubtitleChanged = Signal()
    busyChanged = Signal()
    notification = Signal(str, str)
    listLoaded = Signal()

    def __init__(self, service: SnapKitService):
        super().__init__()
        self._service = service
        self._model = AppListModel(self)
        self._page_title = "SnapKit"
        self._page_subtitle = ""
        self._busy = False
        self._local_filter = "all"
        self._current_view_id = "local_scan"
        self._search_text = ""

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property(str, notify=pageTitleChanged)
    def pageTitle(self) -> str:
        return self._page_title

    @Property(str, notify=pageSubtitleChanged)
    def pageSubtitle(self) -> str:
        return self._page_subtitle

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Slot(str, str)
    def refresh(self, view_id: str, search_text: str = ""):
        self._set_busy(True)
        try:
            self._load_view(view_id, search_text)
        except Exception as exc:
            self.notification.emit("error", f"加载失败: {exc}")
        finally:
            self._set_busy(False)

    @Slot(str, str)
    def scanAndRefresh(self, view_id: str, search_text: str = ""):
        self._set_busy(True)
        try:
            ok, message = self._service.scan_apps()
            self.notification.emit("success" if ok else "error", message)
            self._load_view(view_id, search_text)
        except Exception as exc:
            self.notification.emit("error", f"扫描失败: {exc}")
        finally:
            self._set_busy(False)

    @Slot(int)
    def activate(self, item_id: int):
        ok, message = self._service.activate_item(item_id)
        self.notification.emit("success" if ok else "error", message)

    @Slot(int, str)
    def action(self, item_id: int, action_name: str):
        ok, message = self._service.perform_action(item_id, action_name)
        self.notification.emit("success" if ok else "error", message)
        if not ok:
            return

        if action_name == "delete":
            self._model.remove_item(item_id)
            return

        if action_name == "pin":
            self._sync_pin_change(item_id, True)
            return

        if action_name == "unpin":
            self._sync_pin_change(item_id, False)

    @Slot(int, str)
    def renameItem(self, item_id: int, new_name: str):
        ok, message = self._service.rename_item(item_id, new_name)
        self.notification.emit("success" if ok else "error", message)

    @Slot(int, str)
    def setCustomIcon(self, item_id: int, icon_file_url: str):
        icon_path = _to_local_path(icon_file_url)
        ok, message = self._service.set_custom_icon(item_id, icon_path)
        self.notification.emit("success" if ok else "error", message)

    @Slot(int, str, str)
    def setLocalFilter(self, filter_index: int, view_id: str, search_text: str = ""):
        mapping = {0: "all", 1: "pinned", 2: "unpinned"}
        self._local_filter = mapping.get(filter_index, "all")
        self.refresh(view_id, search_text)

    @Slot(int, str, str, str, str, str, str, str)
    def quickAdd(
        self,
        type_index: int,
        name: str,
        target: str,
        note: str,
        icon_path: str,
        source_mode: str,
        view_id: str,
        search_text: str = "",
    ):
        mapping = {
            0: "local_app",
            1: "wish",
            2: "website",
            3: "document",
            4: "image",
            5: "video",
        }
        item_type = mapping.get(type_index)
        if not item_type:
            self.notification.emit("error", "未知的快速添加类型")
            return

        ok, message = self._service.quick_add(
            item_type=item_type,
            name=name,
            target=target,
            note=note,
            icon_path=icon_path,
            source_mode=source_mode,
        )
        self.notification.emit("success" if ok else "error", message)
        if ok:
            self.refresh(view_id, search_text)

    def _load_view(self, view_id: str, search_text: str):
        self._current_view_id = view_id
        self._search_text = search_text

        title, subtitle, items = self._service.load_view(
            view_id=view_id,  # type: ignore[arg-type]
            search=search_text,
            local_filter=self._local_filter,
        )
        self._page_title = title
        self._page_subtitle = subtitle
        self.pageTitleChanged.emit()
        self.pageSubtitleChanged.emit()
        self._model.set_items(items)
        self.listLoaded.emit()

    def _sync_pin_change(self, item_id: int, pinned: bool):
        if self._current_view_id == "local_scan":
            if self._local_filter == "all":
                self._model.set_item_pinned(item_id, pinned)
            else:
                self._reload_current_view()
            return

        if self._current_view_id == "installed":
            if pinned:
                self._reload_current_view()
            else:
                self._model.remove_item(item_id)
            return

        self._reload_current_view()

    def _reload_current_view(self):
        self._set_busy(True)
        try:
            self._load_view(self._current_view_id, self._search_text)
        except Exception as exc:
            self.notification.emit("error", f"刷新失败: {exc}")
        finally:
            self._set_busy(False)

    def _set_busy(self, value: bool):
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()


def _to_local_path(value: str) -> str:
    if value.startswith("file:///"):
        parsed = urlparse(value)
        return unquote(parsed.path.lstrip("/")).replace("/", "\\")
    return value
