"""Windows software scanner with multi-source merge and filtering."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp

REGISTRY_PATHS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]

_COMPONENT_KEYWORDS = {
    "intellisense",
    "sdk",
    "runtime",
    "redistributable",
    "hotfix",
    "security update",
    "update for",
    "language pack",
    "driver package",
    "winappdeploy",
    "filehandler",
    "minshell",
    "tipsmsi",
}

_ALLOWED_FILE_SUFFIXES = {".exe", ".lnk", ".bat", ".cmd", ".msc"}


def scan_registry(
    actionable_only: bool = True,
    include_system_components: bool = False,
    include_appx: bool = False,
    include_msi: bool = True,
) -> list[dict]:
    """Scan installed software from multiple Windows sources.

    Args:
        actionable_only: Keep only launchable/uninstallable entries.
        include_system_components: Keep entries usually treated as components/updates.
        include_appx: Include Microsoft Store (Appx) packages.
        include_msi: Include MSI product enumeration.
    """
    if platform.system() != "Windows":
        return []

    apps: list[dict] = []
    apps.extend(_scan_arp_registry(include_system_components=include_system_components))

    if include_msi:
        apps.extend(_scan_msi_products(include_system_components=include_system_components))

    if include_appx:
        apps.extend(_scan_appx_packages(include_system_components=include_system_components))

    apps = _merge_duplicates(apps)

    if actionable_only:
        apps = [app for app in apps if _is_actionable(app)]

    return apps


def _scan_arp_registry(include_system_components: bool) -> list[dict]:
    import winreg

    apps: list[dict] = []
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for reg_path in REGISTRY_PATHS:
            try:
                key = winreg.OpenKey(hive, reg_path)
            except OSError:
                continue
            try:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        i += 1
                    except OSError:
                        break

                    try:
                        subkey = winreg.OpenKey(key, subkey_name)
                    except OSError:
                        continue

                    app = _read_subkey(subkey, subkey_name, reg_path, include_system_components)
                    if app:
                        apps.append(app)
                    winreg.CloseKey(subkey)
            finally:
                winreg.CloseKey(key)
    return apps


def _read_subkey(subkey, subkey_name: str, reg_path: str, include_system_components: bool) -> dict | None:
    import winreg

    def _val(name: str) -> str | None:
        try:
            value = winreg.QueryValueEx(subkey, name)[0]
            return str(value) if value is not None else None
        except OSError:
            return None

    def _dword(name: str) -> int | None:
        try:
            value = winreg.QueryValueEx(subkey, name)[0]
            return int(value)
        except (OSError, ValueError, TypeError):
            return None

    display_name = _val("DisplayName")
    if not display_name:
        return None

    system_component = _dword("SystemComponent")
    release_type = _val("ReleaseType")
    parent_key = _val("ParentKeyName")
    parent_name = _val("ParentDisplayName")

    if not include_system_components and _should_skip_arp_entry(
        display_name,
        system_component,
        release_type,
        parent_key,
        parent_name,
    ):
        return None

    display_icon = _normalize_display_icon(_val("DisplayIcon"))
    uninstall_command = _normalize_command(_val("QuietUninstallString") or _val("UninstallString"))
    install_location = _normalize_install_location(_val("InstallLocation"), display_icon)

    return {
        "name": display_name.strip(),
        "publisher": _normalize_text(_val("Publisher")),
        "display_icon": display_icon,
        "uninstall_command": uninstall_command,
        "install_location": install_location,
        "version": _normalize_text(_val("DisplayVersion")),
        "registry_key": f"{reg_path}\\{subkey_name}",
    }


def _scan_msi_products(include_system_components: bool) -> list[dict]:
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return []

    ERROR_SUCCESS = 0
    ERROR_NO_MORE_ITEMS = 259

    msi = ctypes.windll.msi  # type: ignore[attr-defined]
    enum_products = msi.MsiEnumProductsW
    get_info = msi.MsiGetProductInfoW

    apps: list[dict] = []
    index = 0
    while True:
        product_code = ctypes.create_unicode_buffer(39)
        result = enum_products(index, product_code)
        if result == ERROR_NO_MORE_ITEMS:
            break
        index += 1
        if result != ERROR_SUCCESS:
            continue

        code = product_code.value
        name = _msi_property(get_info, code, "InstalledProductName") or _msi_property(
            get_info, code, "ProductName"
        )
        if not name:
            continue

        if not include_system_components and _is_probably_component(name):
            continue

        publisher = _msi_property(get_info, code, "Publisher")
        version = _msi_property(get_info, code, "VersionString")
        install_location = _normalize_install_location(
            _msi_property(get_info, code, "InstallLocation"),
            None,
        )

        apps.append(
            {
                "name": name,
                "publisher": _normalize_text(publisher),
                "display_icon": None,
                "uninstall_command": f"msiexec /x {code}",
                "install_location": install_location,
                "version": _normalize_text(version),
                "registry_key": f"MSI::{code}",
            }
        )

    return apps


def _msi_property(get_info, product_code: str, prop: str) -> str | None:
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None

    ERROR_SUCCESS = 0
    ERROR_MORE_DATA = 234

    buf_chars = 256
    for _ in range(4):
        buf = ctypes.create_unicode_buffer(buf_chars)
        size = wintypes.DWORD(buf_chars)
        result = get_info(product_code, prop, buf, ctypes.byref(size))
        if result == ERROR_SUCCESS:
            return _normalize_text(buf.value)
        if result == ERROR_MORE_DATA:
            buf_chars = max(buf_chars * 2, int(size.value) + 1)
            continue
        return None

    return None


def _scan_appx_packages(include_system_components: bool) -> list[dict]:
    ps = (
        "$ErrorActionPreference='SilentlyContinue'; "
        "Get-AppxPackage | "
        "Select-Object Name,PublisherDisplayName,Version,InstallLocation,"
        "IsFramework,IsResourcePackage,PackageFamilyName,PackageFullName | "
        "ConvertTo-Json -Depth 3"
    )

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except Exception:
        return []

    if proc.returncode != 0 or not proc.stdout.strip():
        return []

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    records = payload if isinstance(payload, list) else [payload]
    apps: list[dict] = []

    for pkg in records:
        if not isinstance(pkg, dict):
            continue
        if pkg.get("IsFramework") or pkg.get("IsResourcePackage"):
            continue

        name = _normalize_text(pkg.get("Name"))
        if not name:
            continue

        if not include_system_components and _is_probably_component(name):
            continue

        package_full_name = _normalize_text(pkg.get("PackageFullName"))
        package_family = _normalize_text(pkg.get("PackageFamilyName"))
        publisher = _normalize_text(pkg.get("PublisherDisplayName"))
        version = _normalize_text(str(pkg.get("Version") or ""))
        install_location = _normalize_install_location(pkg.get("InstallLocation"), None)

        uninstall_command = None
        if package_full_name:
            uninstall_command = (
                "powershell -NoProfile -ExecutionPolicy Bypass -Command "
                f"\"Get-AppxPackage -Package '{package_full_name}' | Remove-AppxPackage\""
            )

        apps.append(
            {
                "name": name,
                "publisher": publisher,
                "display_icon": None,
                "uninstall_command": uninstall_command,
                "install_location": install_location,
                "version": version,
                "registry_key": f"APPX::{package_family or package_full_name or name}",
            }
        )

    return apps


def _merge_duplicates(apps: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for app in apps:
        key = _dedupe_key(app)
        existing = merged.get(key)
        if not existing:
            merged[key] = app
            continue

        winner, loser = _pick_better(existing, app)
        merged_record = dict(winner)
        for field in (
            "publisher",
            "version",
            "install_location",
            "display_icon",
            "uninstall_command",
        ):
            if not merged_record.get(field) and loser.get(field):
                merged_record[field] = loser[field]
        merged[key] = merged_record

    return list(merged.values())


def _dedupe_key(app: dict) -> str:
    name = _normalize_key_text(app.get("name"))
    publisher = _normalize_key_text(app.get("publisher"))
    location = _normalize_key_text(app.get("install_location"))

    if name and publisher:
        return f"{name}|{publisher}"
    if name and location:
        return f"{name}|{location}"

    return _normalize_key_text(app.get("registry_key")) or name or repr(sorted(app.items()))


def _pick_better(a: dict, b: dict) -> tuple[dict, dict]:
    score_a = _quality_score(a)
    score_b = _quality_score(b)
    return (a, b) if score_a >= score_b else (b, a)


def _quality_score(app: dict) -> int:
    score = 0
    if _has_launch_candidate(app):
        score += 6
    if _has_uninstall_candidate(app.get("uninstall_command")):
        score += 3
    if app.get("publisher"):
        score += 1
    if app.get("version"):
        score += 1
    if _is_probably_component(app.get("name") or ""):
        score -= 4
    if str(app.get("registry_key") or "").startswith("APPX::"):
        score -= 1
    return score


def _is_actionable(app: dict) -> bool:
    has_launch = _has_launch_candidate(app)
    has_folder = _has_folder_candidate(app)
    has_uninstall = _has_uninstall_candidate(app.get("uninstall_command"))

    if has_launch:
        return True

    # Keep uninstall-only entries only when they still point to a resolvable local folder.
    if has_uninstall and has_folder and not _is_probably_component(app.get("name") or ""):
        return True

    return False


def _has_launch_candidate(app: dict) -> bool:
    for raw in (app.get("install_location"), app.get("display_icon")):
        path = _path_from_text(raw)
        if not path:
            continue

        if path.is_file() and path.suffix.lower() in _ALLOWED_FILE_SUFFIXES:
            return True

        if path.is_dir():
            try:
                if list(path.glob("*.exe")):
                    return True
                # one-level recursive check
                for child in path.iterdir():
                    if child.is_dir() and list(child.glob("*.exe")):
                        return True
            except OSError:
                continue

    return False


def _has_uninstall_candidate(command: str | None) -> bool:
    if not command:
        return False

    command = command.strip()
    if not command:
        return False

    low = command.lower()
    if low.startswith("msiexec") or low.startswith("powershell"):
        return True

    path = _path_from_text(command)
    return bool(path and path.exists())


def _should_skip_arp_entry(
    display_name: str,
    system_component: int | None,
    release_type: str | None,
    parent_key: str | None,
    parent_name: str | None,
) -> bool:
    if system_component == 1:
        return True

    if parent_key or parent_name:
        return True

    if release_type and release_type.lower() in {
        "update",
        "hotfix",
        "security update",
    }:
        return True

    if re.search(r"\bKB\d{4,}\b", display_name, flags=re.IGNORECASE):
        return True

    return _is_probably_component(display_name)


def _is_probably_component(name: str) -> bool:
    lowered = name.lower()
    normalized = lowered.strip()
    for token in _COMPONENT_KEYWORDS:
        if token in lowered:
            return True

    # noise patterns frequently seen in system entries
    if normalized.startswith("winrt "):
        return True
    if re.match(r"^vs_[a-z0-9_]+$", normalized):
        return True

    return False


def _has_folder_candidate(app: dict) -> bool:
    for raw in (app.get("install_location"), app.get("display_icon")):
        path = _path_from_text(raw)
        if not path:
            continue

        if path.is_dir():
            return True
        if path.is_file():
            return path.parent.exists()

    return False


def load_mock_data() -> list[dict]:
    """Return mock app data for development/testing."""
    return list(MOCK_APPS)


def _normalize_display_icon(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().strip('"')
    if "," in cleaned:
        cleaned = cleaned.split(",", 1)[0].strip().strip('"')
    return cleaned or None


def _normalize_install_location(value: str | None, display_icon: str | None) -> str | None:
    primary = _path_from_text(value)
    if primary:
        return str(primary)

    icon = _path_from_text(display_icon)
    if icon:
        return str(icon)

    return _normalize_text(value) or _normalize_text(display_icon)


def _normalize_command(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip() or None


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_key_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _path_from_text(raw: str | None) -> Path | None:
    text = _normalize_text(raw)
    if not text:
        return None

    text = text.strip('"')

    if "," in text and ":\\" in text:
        text = text.split(",", 1)[0].strip().strip('"')

    lowered = text.lower()
    for suffix in (".exe", ".msi", ".lnk", ".bat", ".cmd", ".msc"):
        idx = lowered.find(suffix)
        if idx != -1:
            text = text[: idx + len(suffix)]
            break

    path = Path(text)
    return path if path.exists() else None


MOCK_APPS = [
    {
        "name": "Mozilla Firefox",
        "publisher": "Mozilla Corporation",
        "install_location": r"C:\Program Files\Mozilla Firefox",
        "version": "120.0",
        "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Firefox",
    },
    {
        "name": "Visual Studio Code",
        "publisher": "Microsoft Corporation",
        "install_location": r"C:\Users\user\AppData\Local\Programs\Microsoft VS Code",
        "version": "1.85.0",
        "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VSCode",
    },
    {
        "name": "Git",
        "publisher": "The Git Development Community",
        "install_location": r"C:\Program Files\Git",
        "version": "2.43.0",
        "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Git",
    },
    {
        "name": "Python 3.12",
        "publisher": "Python Software Foundation",
        "install_location": r"C:\Users\user\AppData\Local\Programs\Python\Python312",
        "version": "3.12.1",
        "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Python312",
    },
    {
        "name": "7-Zip",
        "publisher": "Igor Pavlov",
        "install_location": r"C:\Program Files\7-Zip",
        "version": "23.01",
        "registry_key": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\7-Zip",
    },
]


def save_scanned_apps(session: Session, apps: list[dict]) -> int:
    """Upsert scanned apps into the database. Returns count of new apps added."""
    return _save_scanned_apps(session, apps, prune_missing=False)


def save_scanned_apps_and_prune(session: Session, apps: list[dict]) -> int:
    """Upsert scanned apps and remove stale registry-derived entries."""
    return _save_scanned_apps(session, apps, prune_missing=True)


def _save_scanned_apps(session: Session, apps: list[dict], prune_missing: bool) -> int:
    """Internal save routine with optional stale-entry pruning."""
    added = 0
    now = datetime.now(UTC)
    scanned_keys: set[str] = set()
    for app_data in apps:
        registry_key = app_data.get("registry_key")
        if registry_key:
            scanned_keys.add(registry_key)

        existing = session.query(InstalledApp).filter_by(registry_key=registry_key).first()
        if existing:
            existing.name = app_data["name"]
            existing.publisher = app_data.get("publisher")
            existing.display_icon = app_data.get("display_icon")
            existing.uninstall_command = app_data.get("uninstall_command")
            existing.install_location = app_data.get("install_location")
            existing.version = app_data.get("version")
            existing.scanned_at = now
        else:
            session.add(InstalledApp(**app_data))
            added += 1

    if prune_missing:
        stale_query = (
            session.query(InstalledApp)
            .filter(InstalledApp.registry_key.is_not(None))
            .filter(~InstalledApp.registry_key.like("MANUAL::%"))
        )
        if scanned_keys:
            stale_query = stale_query.filter(~InstalledApp.registry_key.in_(scanned_keys))

        stale_apps = stale_query.all()
        if stale_apps:
            stale_ids = [app.id for app in stale_apps]
            stale_name_set = {
                app.id: (app.custom_name or app.name).strip()
                for app in stale_apps
                if (app.custom_name or app.name)
            }
            existing_wishes = {
                name.lower()
                for (name,) in session.query(NotInstalledApp.name).all()
                if name and name.strip()
            }

            pinned_stale = (
                session.query(PinnedApp)
                .filter(PinnedApp.installed_app_id.in_(stale_ids))
                .all()
            )
            for pin in pinned_stale:
                app_name = stale_name_set.get(pin.installed_app_id, "").strip()
                if not app_name:
                    continue
                key = app_name.lower()
                if key in existing_wishes:
                    continue
                session.add(
                    NotInstalledApp(
                        name=app_name,
                        description="来自已收藏，当前未安装",
                    )
                )
                existing_wishes.add(key)

            session.query(PinnedApp).filter(PinnedApp.installed_app_id.in_(stale_ids)).delete(
                synchronize_session=False
            )
            for app in stale_apps:
                session.delete(app)

    session.commit()
    return added
