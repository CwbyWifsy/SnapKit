"""图标提取模块 - 从 exe 文件提取图标."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QIcon

# 图标缓存
_icon_cache: dict[str, "QIcon"] = {}


def _get_default_icon() -> "QIcon":
    """返回默认应用图标."""
    from PySide6.QtWidgets import QStyle, QApplication

    app = QApplication.instance()
    if app:
        return app.style().standardIcon(QStyle.SP_ComputerIcon)

    from PySide6.QtGui import QIcon
    return QIcon()


def _extract_icon_windows(exe_path: str) -> "QIcon | None":
    """Windows 下从 exe 提取图标."""
    try:
        import win32gui
        import win32ui
        import win32con
        from PySide6.QtGui import QIcon, QPixmap, QImage

        # 获取大图标
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        if not large:
            return None

        icon_handle = large[0]

        # 创建设备上下文
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, 32, 32)

        hdc_mem = hdc.CreateCompatibleDC()
        hdc_mem.SelectObject(hbmp)
        hdc_mem.FillSolidRect((0, 0, 32, 32), 0x00000000)

        win32gui.DrawIconEx(
            hdc_mem.GetSafeHdc(), 0, 0, icon_handle,
            32, 32, 0, None, win32con.DI_NORMAL
        )

        # 转换为 QPixmap
        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)

        image = QImage(
            bmpstr, bmpinfo['bmWidth'], bmpinfo['bmHeight'],
            QImage.Format_ARGB32_Premultiplied
        )
        pixmap = QPixmap.fromImage(image)

        # 清理
        win32gui.DestroyIcon(icon_handle)
        for ico in large[1:] + small:
            win32gui.DestroyIcon(ico)

        hdc_mem.DeleteDC()
        hdc.DeleteDC()
        hbmp.DeleteObject()

        return QIcon(pixmap)

    except Exception:
        return None


def _extract_icon_windows_simple(exe_path: str) -> "QIcon | None":
    """Windows 下使用简化方法提取图标."""
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QFileIconProvider
        from PySide6.QtCore import QFileInfo

        file_info = QFileInfo(exe_path)
        if file_info.exists():
            provider = QFileIconProvider()
            icon = provider.icon(file_info)
            if not icon.isNull():
                return icon
    except Exception:
        pass
    return None


def extract_icon(exe_path: str | None) -> "QIcon":
    """从 exe 文件提取图标.

    Args:
        exe_path: exe 文件路径

    Returns:
        QIcon 对象，提取失败时返回默认图标
    """
    if not exe_path:
        return _get_default_icon()

    # 检查缓存
    if exe_path in _icon_cache:
        return _icon_cache[exe_path]

    icon = None

    # 检查文件是否存在
    path = Path(exe_path)
    if not path.exists():
        return _get_default_icon()

    # Windows 下尝试提取
    if sys.platform == "win32":
        # 先尝试简单方法（使用 Qt 的 QFileIconProvider）
        icon = _extract_icon_windows_simple(exe_path)

        # 如果简单方法失败，尝试 win32 API
        if icon is None or icon.isNull():
            icon = _extract_icon_windows(exe_path)

    # 如果提取失败，使用默认图标
    if icon is None or icon.isNull():
        icon = _get_default_icon()

    # 缓存结果
    _icon_cache[exe_path] = icon
    return icon


def clear_icon_cache():
    """清除图标缓存."""
    _icon_cache.clear()


def get_resource_icon(resource_type: str) -> "QIcon":
    """根据资源类型返回对应图标.

    Args:
        resource_type: 资源类型 (file, folder, url)

    Returns:
        对应的 QIcon
    """
    from PySide6.QtWidgets import QStyle, QApplication

    app = QApplication.instance()
    if not app:
        from PySide6.QtGui import QIcon
        return QIcon()

    style = app.style()

    icon_map = {
        "file": QStyle.SP_FileIcon,
        "folder": QStyle.SP_DirIcon,
        "url": QStyle.SP_DriveNetIcon,
    }

    icon_type = icon_map.get(resource_type, QStyle.SP_FileIcon)
    return style.standardIcon(icon_type)
