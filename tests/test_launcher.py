"""Tests for launcher module."""

import os
import tempfile
from pathlib import Path

from snapkit.launcher import infer_exe, _has_args


def test_infer_exe_empty():
    assert infer_exe("") is None
    assert infer_exe(None) is None


def test_infer_exe_nonexistent_dir():
    assert infer_exe(r"C:\nonexistent\path\12345") is None


def test_infer_exe_matches_app_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create fake exe files
        (Path(tmpdir) / "firefox.exe").touch()
        (Path(tmpdir) / "updater.exe").touch()

        result = infer_exe(tmpdir, "Firefox")
        assert result is not None
        assert "firefox.exe" in result.lower()


def test_infer_exe_fallback_first():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "alpha.exe").touch()
        (Path(tmpdir) / "beta.exe").touch()

        result = infer_exe(tmpdir, "NoMatch")
        assert result is not None
        assert "alpha.exe" in result.lower()


def test_has_args():
    assert _has_args("notepad.exe") is False
    assert _has_args('"C:\\Program Files\\app.exe"') is False
    assert _has_args("notepad.exe file.txt") is True
    assert _has_args('"C:\\Program Files\\app.exe" --flag') is True
