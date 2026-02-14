"""Application launcher – exe inference and subprocess launch."""

import os
import platform
import subprocess
from pathlib import Path


def infer_exe(install_location: str, app_name: str = "") -> str | None:
    """Best-effort inference of the main executable from an install directory.

    Strategy:
    1. Look for an exe whose stem matches (or contains) the app name.
    2. Fall back to the first exe found in the directory root.
    """
    if not install_location:
        return None

    loc = Path(install_location)
    if not loc.is_dir():
        return None

    exes = list(loc.glob("*.exe"))
    if not exes:
        return None

    # Try to match app name
    if app_name:
        name_lower = app_name.lower().replace(" ", "")
        for exe in exes:
            if name_lower in exe.stem.lower().replace(" ", ""):
                return str(exe)

    # Fallback: first exe alphabetically
    exes.sort(key=lambda p: p.name.lower())
    return str(exes[0])


def launch_app(command: str) -> subprocess.Popen | None:
    """Launch an application via *command*.

    On Windows uses os.startfile for simple exe paths, otherwise subprocess.
    Returns the Popen object (or None if startfile was used).
    """
    if platform.system() == "Windows" and not _has_args(command):
        os.startfile(command)  # type: ignore[attr-defined]
        return None

    return subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _has_args(command: str) -> bool:
    """Check if command string contains arguments beyond the executable."""
    # Simple heuristic: if there's a space outside of quotes, there are args
    in_quote = False
    for ch in command:
        if ch == '"':
            in_quote = not in_quote
        elif ch == " " and not in_quote:
            return True
    return False
