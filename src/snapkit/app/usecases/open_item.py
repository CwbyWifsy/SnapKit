from __future__ import annotations

import ctypes
import os
import platform
import shlex
import subprocess
import webbrowser
from pathlib import Path

from snapkit.core.entities import UiItem
from snapkit.launcher import infer_exe, launch_app


def activate_item(item: UiItem, as_admin: bool = False) -> tuple[bool, str]:
    if item.kind in {"local", "pinned"}:
        command = _resolve_launch_command(item)
        if not command:
            return False, f"无法启动 {item.title}，未找到可执行文件"

        if as_admin:
            return _launch_as_admin(command, item.title)

        launch_app(command)
        return True, f"已启动: {item.title}"

    if item.kind == "wish":
        if item.download_url:
            webbrowser.open(item.download_url)
            return True, f"已打开下载链接: {item.title}"
        return False, f"{item.title} 未配置下载链接"

    if item.kind == "resource":
        if not item.path:
            return False, f"{item.title} 缺少资源路径"
        _open_resource(item.path, item.resource_type)
        return True, f"已打开: {item.title}"

    return False, "不支持的操作"


def open_item_folder(item: UiItem) -> tuple[bool, str]:
    target = _resolve_folder_target(item)
    if not target:
        return False, f"{item.title} 未找到可打开的目录"

    _open_path(target)
    return True, f"已打开目录: {target}"


def uninstall_item(item: UiItem) -> tuple[bool, str]:
    if not item.uninstall_command:
        return False, f"{item.title} 缺少卸载命令"

    subprocess.Popen(item.uninstall_command, shell=True)
    return True, f"已发起卸载: {item.title}"


def _resolve_launch_command(item: UiItem) -> str | None:
    launch_suffixes = {".exe", ".lnk", ".bat", ".cmd"}

    if item.launch_command:
        return item.launch_command

    icon_path = _safe_path(item.icon_path)
    if icon_path and icon_path.is_file() and icon_path.suffix.lower() in launch_suffixes:
        return str(icon_path)

    location = _safe_path(item.install_location)
    if location and location.is_file() and location.suffix.lower() in launch_suffixes:
        return str(location)

    if location and location.is_dir():
        inferred = infer_exe(str(location), item.title)
        if inferred:
            return inferred

    if icon_path and icon_path.is_dir():
        inferred = infer_exe(str(icon_path), item.title)
        if inferred:
            return inferred

    return None


def _resolve_folder_target(item: UiItem) -> str | None:
    candidates = [item.install_location, item.icon_path, item.path]
    for candidate in candidates:
        path = _safe_path(candidate)
        if not path:
            continue
        if path.is_dir():
            return str(path)
        if path.is_file():
            return str(path.parent)
    return None


def _open_resource(target: str, resource_type: str | None):
    lowered = target.lower()
    if resource_type == "url" or lowered.startswith("http://") or lowered.startswith("https://"):
        webbrowser.open(target)
        return

    _open_path(target)


def _open_path(target: str):
    if platform.system() == "Windows":
        os.startfile(target)  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def _launch_as_admin(command: str, title: str) -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "管理员启动仅支持 Windows"

    exe, params = _split_command(command)
    if not exe:
        return False, f"无法解析启动命令: {title}"

    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    if result <= 32:
        return False, f"管理员启动失败: {title}"
    return True, f"已管理员启动: {title}"


def _split_command(command: str) -> tuple[str | None, str | None]:
    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        parts = [command]

    if not parts:
        return None, None

    exe = parts[0]
    params = subprocess.list2cmdline(parts[1:]) if len(parts) > 1 else None
    return exe, params


def _safe_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None
