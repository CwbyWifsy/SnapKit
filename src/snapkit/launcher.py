"""Application launcher - exe inference and subprocess launch."""

import os
import platform
import subprocess
from pathlib import Path


def infer_exe(install_location: str, app_name: str = "") -> str | None:
    """Best-effort inference of the main executable.

    Strategy:
    1. If install_location is already an .exe, use it.
    2. Search exes in directory root.
    3. Search exes recursively up to depth 2.
    4. Prefer names matching app_name; fallback to shortest sensible path.
    """
    if not install_location:
        return None

    loc = Path(install_location)
    if loc.is_file() and loc.suffix.lower() == ".exe":
        return str(loc)

    if not loc.is_dir():
        return None

    candidates = _collect_exes(loc)
    if not candidates:
        return None

    if app_name:
        app_tokens = _normalize(app_name)
        for exe in candidates:
            stem = _normalize(exe.stem)
            if app_tokens and all(token in stem for token in app_tokens):
                return str(exe)

    candidates.sort(key=lambda p: (p.name.lower(), len(str(p))))
    return str(candidates[0])


def launch_app(command: str) -> subprocess.Popen | None:
    """Launch an application via *command*."""
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
    in_quote = False
    for ch in command:
        if ch == '"':
            in_quote = not in_quote
        elif ch == " " and not in_quote:
            return True
    return False


def _collect_exes(root: Path, max_depth: int = 2) -> list[Path]:
    exes = list(root.glob("*.exe"))

    for path in root.rglob("*.exe"):
        rel_depth = len(path.relative_to(root).parts) - 1
        if rel_depth <= max_depth and path not in exes:
            exes.append(path)

    return exes


def _normalize(name: str) -> list[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in name)
    return [token for token in cleaned.split() if token]
