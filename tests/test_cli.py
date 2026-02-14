"""Tests for CLI commands."""

from typer.testing import CliRunner

from snapkit.cli import app

runner = CliRunner()


def test_scan_mock():
    result = runner.invoke(app, ["scan", "--mock"])
    assert result.exit_code == 0
    assert "5 apps found" in result.output


def test_list_installed_empty():
    result = runner.invoke(app, ["list-installed"])
    # May show "No installed apps" or a table depending on prior state
    assert result.exit_code == 0
