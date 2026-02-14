"""Windows registry scanner for installed applications."""

import platform
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from snapkit.models import InstalledApp

REGISTRY_PATHS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
]


def scan_registry() -> list[dict]:
    """Scan Windows registry for installed apps. Returns empty list on non-Windows."""
    if platform.system() != "Windows":
        return []

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
                    app = _read_subkey(subkey, subkey_name, reg_path)
                    if app:
                        apps.append(app)
                    winreg.CloseKey(subkey)
            finally:
                winreg.CloseKey(key)
    return apps


def _read_subkey(subkey, subkey_name: str, reg_path: str) -> dict | None:
    """Read app info from a single registry subkey."""
    import winreg

    def _val(name: str) -> str | None:
        try:
            return winreg.QueryValueEx(subkey, name)[0]
        except OSError:
            return None

    display_name = _val("DisplayName")
    if not display_name:
        return None

    return {
        "name": display_name,
        "publisher": _val("Publisher"),
        "install_location": _val("InstallLocation"),
        "version": _val("DisplayVersion"),
        "registry_key": f"{reg_path}\\{subkey_name}",
    }


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


def load_mock_data() -> list[dict]:
    """Return mock app data for development/testing."""
    return list(MOCK_APPS)


def save_scanned_apps(session: Session, apps: list[dict]) -> int:
    """Upsert scanned apps into the database. Returns count of new apps added."""
    added = 0
    now = datetime.now(UTC)
    for app_data in apps:
        existing = (
            session.query(InstalledApp)
            .filter_by(registry_key=app_data.get("registry_key"))
            .first()
        )
        if existing:
            existing.name = app_data["name"]
            existing.publisher = app_data.get("publisher")
            existing.install_location = app_data.get("install_location")
            existing.version = app_data.get("version")
            existing.scanned_at = now
        else:
            session.add(InstalledApp(**app_data))
            added += 1
    session.commit()
    return added
