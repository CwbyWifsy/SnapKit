"""Export/import SnapKit data as a zip bundle."""

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy.orm import Session

from snapkit.models import InstalledApp, NotInstalledApp, PinnedApp, ResourceItem


def export_bundle(session: Session, output_path: Path, include_resources: list[int] | None = None) -> Path:
    """Export DB data + optional resource files into a zip bundle.

    Args:
        session: Active DB session.
        output_path: Destination zip file path.
        include_resources: List of ResourceItem IDs whose files to include.
                          None means include all local files.
    """
    data = {
        "exported_at": datetime.now(UTC).isoformat(),
        "installed_apps": _dump_installed(session),
        "pinned_apps": _dump_pinned(session),
        "not_installed_apps": _dump_not_installed(session),
        "resource_items": _dump_resources(session),
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        # Write JSON manifest
        manifest = tmp / "snapkit_data.json"
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Copy resource files
        resources = session.query(ResourceItem).all()
        if include_resources is not None:
            resources = [r for r in resources if r.id in include_resources]

        files_dir = tmp / "files"
        files_dir.mkdir()
        file_map: dict[int, str] = {}
        for res in resources:
            if res.resource_type in ("file", "folder") and Path(res.path).exists():
                src = Path(res.path)
                dest_name = f"{res.id}_{src.name}"
                if src.is_file():
                    shutil.copy2(src, files_dir / dest_name)
                    file_map[res.id] = dest_name
                elif src.is_dir():
                    shutil.copytree(src, files_dir / dest_name)
                    file_map[res.id] = dest_name

        # Write file map
        if file_map:
            (tmp / "file_map.json").write_text(
                json.dumps(file_map, indent=2), encoding="utf-8"
            )

        # Create zip
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w") as zf:
            for f in tmp.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(tmp))

    return output_path


def import_bundle(session: Session, zip_path: Path, restore_files_to: Path | None = None) -> dict:
    """Import a zip bundle into the database.

    Args:
        session: Active DB session.
        zip_path: Path to the zip bundle.
        restore_files_to: Directory to extract resource files into.

    Returns:
        Summary dict with counts of imported items.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)

        manifest = tmp / "snapkit_data.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))

        counts = {
            "installed_apps": _load_installed(session, data.get("installed_apps", [])),
            "pinned_apps": _load_pinned(session, data.get("pinned_apps", [])),
            "not_installed_apps": _load_not_installed(session, data.get("not_installed_apps", [])),
            "resource_items": _load_resources(session, data.get("resource_items", [])),
        }

        # Restore files
        file_map_path = tmp / "file_map.json"
        if file_map_path.exists() and restore_files_to:
            file_map = json.loads(file_map_path.read_text(encoding="utf-8"))
            restore_files_to = Path(restore_files_to)
            restore_files_to.mkdir(parents=True, exist_ok=True)
            files_dir = tmp / "files"
            for _res_id, fname in file_map.items():
                src = files_dir / fname
                if src.exists():
                    dest = restore_files_to / fname
                    if src.is_dir():
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dest)

        session.commit()
    return counts


# ── Serialization helpers ─────────────────────────────────────────────


def _dump_installed(session: Session) -> list[dict]:
    return [
        {
            "name": a.name,
            "publisher": a.publisher,
            "install_location": a.install_location,
            "version": a.version,
            "registry_key": a.registry_key,
            "tags": a.tags,
        }
        for a in session.query(InstalledApp).all()
    ]


def _dump_pinned(session: Session) -> list[dict]:
    return [
        {
            "installed_app_registry_key": p.installed_app.registry_key,
            "launch_command": p.launch_command,
            "tags": p.tags,
        }
        for p in session.query(PinnedApp).all()
    ]


def _dump_not_installed(session: Session) -> list[dict]:
    return [
        {
            "name": a.name,
            "description": a.description,
            "download_url": a.download_url,
            "tags": a.tags,
        }
        for a in session.query(NotInstalledApp).all()
    ]


def _dump_resources(session: Session) -> list[dict]:
    return [
        {
            "name": r.name,
            "path": r.path,
            "resource_type": r.resource_type,
            "tags": r.tags,
        }
        for r in session.query(ResourceItem).all()
    ]


# ── Deserialization helpers ───────────────────────────────────────────


def _load_installed(session: Session, items: list[dict]) -> int:
    count = 0
    for item in items:
        existing = session.query(InstalledApp).filter_by(registry_key=item.get("registry_key")).first()
        if not existing:
            session.add(InstalledApp(**item))
            count += 1
    return count


def _load_pinned(session: Session, items: list[dict]) -> int:
    count = 0
    for item in items:
        reg_key = item.get("installed_app_registry_key")
        if not reg_key:
            continue
        installed = session.query(InstalledApp).filter_by(registry_key=reg_key).first()
        if not installed:
            continue
        existing = session.query(PinnedApp).filter_by(installed_app_id=installed.id).first()
        if not existing:
            session.add(PinnedApp(
                installed_app_id=installed.id,
                launch_command=item.get("launch_command"),
                tags=item.get("tags"),
            ))
            count += 1
    return count


def _load_not_installed(session: Session, items: list[dict]) -> int:
    count = 0
    for item in items:
        existing = session.query(NotInstalledApp).filter_by(name=item["name"]).first()
        if not existing:
            session.add(NotInstalledApp(**item))
            count += 1
    return count


def _load_resources(session: Session, items: list[dict]) -> int:
    count = 0
    for item in items:
        existing = (
            session.query(ResourceItem)
            .filter_by(name=item["name"], path=item["path"])
            .first()
        )
        if not existing:
            session.add(ResourceItem(**item))
            count += 1
    return count
