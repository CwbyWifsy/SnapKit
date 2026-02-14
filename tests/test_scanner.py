"""Tests for scanner module."""

from snapkit.models import InstalledApp
from snapkit.scanner import load_mock_data, save_scanned_apps


def test_load_mock_data():
    data = load_mock_data()
    assert len(data) == 5
    assert all("name" in d for d in data)


def test_save_scanned_apps(session):
    apps = load_mock_data()
    added = save_scanned_apps(session, apps)
    assert added == 5
    assert session.query(InstalledApp).count() == 5


def test_save_scanned_apps_upsert(session):
    apps = load_mock_data()
    save_scanned_apps(session, apps)
    # Second scan should not add duplicates
    added = save_scanned_apps(session, apps)
    assert added == 0
    assert session.query(InstalledApp).count() == 5


def test_save_scanned_apps_updates_version(session):
    apps = load_mock_data()
    save_scanned_apps(session, apps)

    apps[0]["version"] = "999.0"
    save_scanned_apps(session, apps)

    result = (
        session.query(InstalledApp)
        .filter_by(registry_key=apps[0]["registry_key"])
        .one()
    )
    assert result.version == "999.0"
