"""Tests for exporter module."""

import tempfile
from pathlib import Path

from snapkit.exporter import export_bundle, import_bundle
from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp, ResourceItem


def _seed_data(session):
    """Seed the database with test data."""
    app1 = InstalledApp(
        name="Firefox",
        publisher="Mozilla",
        version="120.0",
        registry_key="HKLM\\Software\\Firefox",
    )
    app2 = InstalledApp(
        name="Git",
        publisher="Git Community",
        version="2.43",
        registry_key="HKLM\\Software\\Git",
    )
    session.add_all([app1, app2])
    session.flush()

    pin = PinnedApp(installed_app_id=app1.id, launch_command="firefox.exe")
    session.add(pin)

    ni = NotInstalledApp(name="Blender", download_url="https://blender.org", tags="3d")
    session.add(ni)

    res = ResourceItem(name="Notes", path="/tmp/notes.txt", resource_type="file")
    session.add(res)
    session.commit()


def test_export_creates_zip(session):
    _seed_data(session)
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "export.zip"
        result = export_bundle(session, out)
        assert result.exists()
        assert result.suffix == ".zip"


def test_roundtrip(session, engine):
    """Export from one session, import into a fresh session."""
    _seed_data(session)

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "bundle.zip"
        export_bundle(session, zip_path)

        # Create a fresh session (same in-memory DB, but clear all data)
        session.query(PinnedApp).delete()
        session.query(InstalledApp).delete()
        session.query(NotInstalledApp).delete()
        session.query(ResourceItem).delete()
        session.commit()

        assert session.query(InstalledApp).count() == 0

        counts = import_bundle(session, zip_path)
        assert counts["installed_apps"] == 2
        assert counts["pinned_apps"] == 1
        assert counts["not_installed_apps"] == 1
        assert counts["resource_items"] == 1


def test_import_no_duplicates(session):
    """Importing twice should not create duplicates."""
    _seed_data(session)

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "bundle.zip"
        export_bundle(session, zip_path)

        # Import on top of existing data
        counts = import_bundle(session, zip_path)
        assert counts["installed_apps"] == 0
        assert counts["not_installed_apps"] == 0
