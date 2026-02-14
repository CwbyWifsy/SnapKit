"""Tests for ORM models."""

from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp, ResourceItem


def test_create_installed_app(session):
    app = InstalledApp(name="Firefox", publisher="Mozilla", version="120.0")
    session.add(app)
    session.commit()

    result = session.query(InstalledApp).one()
    assert result.name == "Firefox"
    assert result.publisher == "Mozilla"
    assert result.scanned_at is not None


def test_pin_app(session):
    app = InstalledApp(name="VSCode", install_location=r"C:\Program Files\VSCode")
    session.add(app)
    session.flush()

    pin = PinnedApp(installed_app_id=app.id, launch_command="code.exe")
    session.add(pin)
    session.commit()

    result = session.query(PinnedApp).one()
    assert result.installed_app.name == "VSCode"
    assert result.launch_command == "code.exe"


def test_not_installed_app(session):
    app = NotInstalledApp(
        name="Blender",
        download_url="https://www.blender.org/download/",
        tags="3d,modeling",
    )
    session.add(app)
    session.commit()

    result = session.query(NotInstalledApp).one()
    assert result.name == "Blender"
    assert result.tags == "3d,modeling"


def test_resource_item(session):
    res = ResourceItem(name="Notes", path=r"C:\Users\me\notes.txt", resource_type="file")
    session.add(res)
    session.commit()

    result = session.query(ResourceItem).one()
    assert result.resource_type == "file"


def test_installed_app_tags(session):
    app = InstalledApp(name="Git", tags="dev,vcs")
    session.add(app)
    session.commit()

    result = session.query(InstalledApp).one()
    assert "dev" in result.tags
