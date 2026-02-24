from __future__ import annotations

from sqlalchemy import Engine

from snapkit.db import get_session
from snapkit.scanner import save_scanned_apps_and_prune, scan_registry


def scan_installed_apps(engine: Engine) -> tuple[int, int]:
    """Scan registry and persist results.

    Returns:
        tuple(found_count, new_count)
    """
    session = get_session(engine)
    try:
        apps = scan_registry()
        if not apps:
            return 0, 0
        added = save_scanned_apps_and_prune(session, apps)
        return len(apps), added
    finally:
        session.close()
