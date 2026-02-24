from __future__ import annotations

from dataclasses import replace
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import QAbstractListModel, QByteArray, QBuffer, QFileInfo, QModelIndex, QIODevice, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileIconProvider

from snapkit.core.entities import UiItem
from snapkit.launcher import infer_exe


class AppListModel(QAbstractListModel):
    ItemIdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    SubtitleRole = Qt.UserRole + 3
    BadgeRole = Qt.UserRole + 4
    KindRole = Qt.UserRole + 5
    IconSourceRole = Qt.UserRole + 6
    IsPinnedRole = Qt.UserRole + 7
    InstallLocationRole = Qt.UserRole + 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[UiItem] = []
        self._icon_sources: list[str] = []
        self._icon_cache: dict[str, str] = {}
        self._icon_provider = QFileIconProvider()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        item = self._items[index.row()]

        if role == self.ItemIdRole:
            return item.item_id
        if role == self.TitleRole:
            return item.title
        if role == self.SubtitleRole:
            return item.subtitle
        if role == self.BadgeRole:
            return item.badge
        if role == self.KindRole:
            return item.kind
        if role == self.IconSourceRole:
            return self._icon_sources[index.row()]
        if role == self.IsPinnedRole:
            return item.is_pinned
        if role == self.InstallLocationRole:
            return item.install_location or item.icon_path or item.path or ""
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            self.ItemIdRole: b"itemId",
            self.TitleRole: b"title",
            self.SubtitleRole: b"subtitle",
            self.BadgeRole: b"badge",
            self.KindRole: b"kind",
            self.IconSourceRole: b"iconSource",
            self.IsPinnedRole: b"isPinned",
            self.InstallLocationRole: b"installLocation",
        }

    def set_items(self, items: list[UiItem]):
        self.beginResetModel()
        self._items = items
        self._icon_sources = [self._build_icon_source(item) for item in items]
        self.endResetModel()

    def set_item_pinned(self, item_id: int, pinned: bool) -> bool:
        for row, item in enumerate(self._items):
            if item.item_id != item_id:
                continue
            if item.is_pinned == pinned:
                return True
            self._items[row] = replace(item, is_pinned=pinned)
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsPinnedRole])
            return True
        return False

    def remove_item(self, item_id: int) -> bool:
        for row, item in enumerate(self._items):
            if item.item_id != item_id:
                continue
            self.beginRemoveRows(QModelIndex(), row, row)
            self._items.pop(row)
            self._icon_sources.pop(row)
            self.endRemoveRows()
            return True
        return False

    def _build_icon_source(self, item: UiItem) -> str:
        website_icon = _build_website_icon(item)
        if website_icon:
            return website_icon

        path = self._resolve_icon_path(item)
        if not path:
            return ""

        cached = self._icon_cache.get(path)
        if cached is not None:
            return cached

        pixmap = self._icon_provider.icon(QFileInfo(path)).pixmap(96, 96)
        source = _icon_to_data_url(_trim_transparent(pixmap))
        self._icon_cache[path] = source
        return source

    def _resolve_icon_path(self, item: UiItem) -> str | None:
        for candidate in (item.icon_path, item.install_location):
            if not candidate:
                continue
            if candidate.lower().startswith("http://") or candidate.lower().startswith("https://"):
                continue

            # install_location often points to a folder; infer exe first.
            inferred = infer_exe(candidate, item.title)
            if inferred:
                return inferred

            info = QFileInfo(candidate)
            if info.exists():
                return candidate

        if item.path and not (item.path.lower().startswith("http://") or item.path.lower().startswith("https://")):
            info = QFileInfo(item.path)
            if info.exists():
                return item.path

        return None


def _icon_to_data_url(pixmap: QPixmap) -> str:
    if pixmap.isNull():
        return ""

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    if not buffer.open(QIODevice.WriteOnly):
        return ""

    pixmap.save(buffer, "PNG")
    encoded = bytes(byte_array.toBase64()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _build_website_icon(item: UiItem) -> str | None:
    if item.kind != "resource" or item.resource_type != "url" or not item.path:
        return None

    raw = item.path.strip()
    if not raw:
        return None

    if "://" not in raw:
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    host = (parsed.hostname or "").strip()
    if not host:
        return None

    # Use icon proxy first; if blocked/unavailable, QML falls back to letter avatar.
    return f"https://icons.duckduckgo.com/ip3/{host}.ico"


def _trim_transparent(pixmap: QPixmap) -> QPixmap:
    if pixmap.isNull():
        return pixmap

    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    width = image.width()
    height = image.height()
    min_x, min_y = width, height
    max_x, max_y = -1, -1

    for y in range(height):
        for x in range(width):
            alpha = (image.pixel(x, y) >> 24) & 0xFF
            if alpha > 10:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x < 0 or max_y < 0:
        return pixmap

    margin = 1
    min_x = max(0, min_x - margin)
    min_y = max(0, min_y - margin)
    max_x = min(width - 1, max_x + margin)
    max_y = min(height - 1, max_y + margin)

    cropped = image.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return QPixmap.fromImage(cropped)
