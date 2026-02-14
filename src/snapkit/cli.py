"""Typer CLI for SnapKit."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from snapkit.db import get_engine, get_session, init_db

app = typer.Typer(help="SnapKit – Windows personal toolbox / launcher.")
console = Console()

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
        init_db(_engine)
    return _engine


def _session():
    return get_session(_get_engine())


# ── Phase 2: Scan / List ──────────────────────────────────────────────


@app.command()
def scan(mock: bool = typer.Option(False, "--mock", help="Use mock data instead of registry")):
    """Scan Windows registry (or mock data) for installed apps."""
    from snapkit.scanner import load_mock_data, save_scanned_apps, scan_registry

    session = _session()
    apps = load_mock_data() if mock else scan_registry()
    if not apps:
        console.print("[yellow]No apps found. Use --mock on non-Windows systems.[/yellow]")
        return
    added = save_scanned_apps(session, apps)
    console.print(f"[green]Scan complete:[/green] {len(apps)} apps found, {added} new.")


@app.command("list-installed")
def list_installed(
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """List all installed apps in the database."""
    from snapkit.models import InstalledApp

    session = _session()
    query = session.query(InstalledApp)
    if tag:
        query = query.filter(InstalledApp.tags.contains(tag))
    apps = query.order_by(InstalledApp.name).all()

    if not apps:
        console.print("[yellow]No installed apps found. Run 'scan' first.[/yellow]")
        return

    table = Table(title="Installed Apps")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Publisher")
    table.add_column("Version")
    table.add_column("Tags")
    for a in apps:
        table.add_row(str(a.id), a.name, a.publisher or "", a.version or "", a.tags or "")
    console.print(table)


# ── Phase 3: Pin / Launch ─────────────────────────────────────────────


@app.command()
def pin(app_id: int = typer.Argument(..., help="ID of the installed app to pin")):
    """Pin an installed app for quick access."""
    from snapkit.models import InstalledApp, PinnedApp

    session = _session()
    installed = session.get(InstalledApp, app_id)
    if not installed:
        console.print(f"[red]No installed app with ID {app_id}.[/red]")
        raise typer.Exit(1)

    existing = session.query(PinnedApp).filter_by(installed_app_id=app_id).first()
    if existing:
        console.print(f"[yellow]{installed.name!r} is already pinned (pin ID {existing.id}).[/yellow]")
        return

    pin_entry = PinnedApp(installed_app_id=app_id)
    session.add(pin_entry)
    session.commit()
    console.print(f"[green]Pinned {installed.name!r} (pin ID {pin_entry.id}).[/green]")


@app.command()
def unpin(pin_id: int = typer.Argument(..., help="ID of the pinned entry to remove")):
    """Unpin an app."""
    from snapkit.models import PinnedApp

    session = _session()
    entry = session.get(PinnedApp, pin_id)
    if not entry:
        console.print(f"[red]No pinned entry with ID {pin_id}.[/red]")
        raise typer.Exit(1)

    name = entry.installed_app.name
    session.delete(entry)
    session.commit()
    console.print(f"[green]Unpinned {name!r}.[/green]")


@app.command("set-launch")
def set_launch(
    pin_id: int = typer.Argument(..., help="Pinned app ID"),
    command: str = typer.Argument(..., help="Launch command or exe path"),
):
    """Set a custom launch command for a pinned app."""
    from snapkit.models import PinnedApp

    session = _session()
    entry = session.get(PinnedApp, pin_id)
    if not entry:
        console.print(f"[red]No pinned entry with ID {pin_id}.[/red]")
        raise typer.Exit(1)

    entry.launch_command = command
    session.commit()
    console.print(f"[green]Launch command for {entry.installed_app.name!r} set to: {command}[/green]")


@app.command("list-pinned")
def list_pinned():
    """List all pinned apps."""
    from snapkit.models import PinnedApp

    session = _session()
    pins = session.query(PinnedApp).all()

    if not pins:
        console.print("[yellow]No pinned apps. Use 'pin <app_id>' to pin one.[/yellow]")
        return

    table = Table(title="Pinned Apps")
    table.add_column("Pin ID", style="dim")
    table.add_column("App Name", style="bold")
    table.add_column("Launch Command")
    table.add_column("Tags")
    for p in pins:
        table.add_row(
            str(p.id),
            p.installed_app.name,
            p.launch_command or "(auto)",
            p.tags or "",
        )
    console.print(table)


@app.command()
def run(pin_id: int = typer.Argument(..., help="Pinned app ID to launch")):
    """Launch a pinned app."""
    from snapkit.launcher import infer_exe, launch_app
    from snapkit.models import PinnedApp

    session = _session()
    entry = session.get(PinnedApp, pin_id)
    if not entry:
        console.print(f"[red]No pinned entry with ID {pin_id}.[/red]")
        raise typer.Exit(1)

    command = entry.launch_command
    if not command:
        loc = entry.installed_app.install_location
        exe = infer_exe(loc, entry.installed_app.name) if loc else None
        if not exe:
            console.print(
                f"[red]Cannot infer exe for {entry.installed_app.name!r}. "
                f"Use 'set-launch {pin_id} <command>' to set manually.[/red]"
            )
            raise typer.Exit(1)
        command = exe

    console.print(f"Launching {entry.installed_app.name!r} → {command}")
    launch_app(command)


# ── Phase 4: Not-installed apps / Resources ──────────────────────────


@app.command("add-notinstalled")
def add_notinstalled(
    name: str = typer.Argument(..., help="App name"),
    url: Optional[str] = typer.Option(None, "--url", help="Download URL"),
    description: Optional[str] = typer.Option(None, "--desc", help="Description"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
):
    """Add a not-yet-installed app to track."""
    from snapkit.models import NotInstalledApp

    session = _session()
    entry = NotInstalledApp(name=name, download_url=url, description=description, tags=tags)
    session.add(entry)
    session.commit()
    console.print(f"[green]Added not-installed app {name!r} (ID {entry.id}).[/green]")


@app.command("list-notinstalled")
def list_notinstalled(
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """List not-installed apps."""
    from snapkit.models import NotInstalledApp

    session = _session()
    query = session.query(NotInstalledApp)
    if tag:
        query = query.filter(NotInstalledApp.tags.contains(tag))
    apps = query.order_by(NotInstalledApp.name).all()

    if not apps:
        console.print("[yellow]No not-installed apps tracked.[/yellow]")
        return

    table = Table(title="Not-Installed Apps")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Download URL")
    table.add_column("Description")
    table.add_column("Tags")
    for a in apps:
        table.add_row(str(a.id), a.name, a.download_url or "", a.description or "", a.tags or "")
    console.print(table)


@app.command("add-resource")
def add_resource(
    name: str = typer.Argument(..., help="Resource name"),
    path: str = typer.Argument(..., help="File path, folder path, or URL"),
    resource_type: str = typer.Option("file", "--type", help="file, folder, or url"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
):
    """Add a resource (file, folder, or URL) to track."""
    from snapkit.models import ResourceItem

    if resource_type not in ("file", "folder", "url"):
        console.print("[red]Type must be one of: file, folder, url[/red]")
        raise typer.Exit(1)

    session = _session()
    entry = ResourceItem(name=name, path=path, resource_type=resource_type, tags=tags)
    session.add(entry)
    session.commit()
    console.print(f"[green]Added resource {name!r} (ID {entry.id}).[/green]")


@app.command("list-resources")
def list_resources(
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """List tracked resources."""
    from snapkit.models import ResourceItem

    session = _session()
    query = session.query(ResourceItem)
    if tag:
        query = query.filter(ResourceItem.tags.contains(tag))
    items = query.order_by(ResourceItem.name).all()

    if not items:
        console.print("[yellow]No resources tracked.[/yellow]")
        return

    table = Table(title="Resources")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Tags")
    for r in items:
        table.add_row(str(r.id), r.name, r.resource_type, r.path, r.tags or "")
    console.print(table)


@app.command("open-resource")
def open_resource(res_id: int = typer.Argument(..., help="Resource ID to open")):
    """Open a resource (file/folder via system handler, URL in browser)."""
    import os
    import platform
    import subprocess
    import webbrowser

    from snapkit.models import ResourceItem

    session = _session()
    entry = session.get(ResourceItem, res_id)
    if not entry:
        console.print(f"[red]No resource with ID {res_id}.[/red]")
        raise typer.Exit(1)

    target = entry.path
    console.print(f"Opening {entry.name!r} → {target}")

    if entry.resource_type == "url":
        webbrowser.open(target)
    elif platform.system() == "Windows":
        os.startfile(target)  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


# ── Phase 5: Export / Import ──────────────────────────────────────────


@app.command("export")
def export_cmd(
    output: str = typer.Argument("snapkit_export.zip", help="Output zip file path"),
):
    """Export all SnapKit data to a zip bundle."""
    from snapkit.exporter import export_bundle

    session = _session()
    result = export_bundle(session, Path(output))
    console.print(f"[green]Exported to {result}[/green]")


@app.command("import")
def import_cmd(
    zip_path: str = typer.Argument(..., help="Path to zip bundle"),
    restore_to: Optional[str] = typer.Option(None, "--restore-to", help="Directory to restore resource files"),
):
    """Import SnapKit data from a zip bundle."""
    from snapkit.exporter import import_bundle

    session = _session()
    p = Path(zip_path)
    if not p.exists():
        console.print(f"[red]File not found: {zip_path}[/red]")
        raise typer.Exit(1)

    restore = Path(restore_to) if restore_to else None
    counts = import_bundle(session, p, restore_files_to=restore)
    console.print("[green]Import complete:[/green]")
    for key, count in counts.items():
        console.print(f"  {key}: {count} new")


# ── Phase 6: GUI ─────────────────────────────────────────────────────


@app.command()
def gui():
    """Launch the SnapKit GUI (requires PySide6)."""
    try:
        from snapkit.gui.main_window import run_gui
    except ImportError:
        console.print(
            "[red]PySide6 is not installed. Install with:[/red]\n"
            "  uv pip install 'snapkit[gui]'"
        )
        raise typer.Exit(1)

    engine = _get_engine()
    run_gui(engine)


if __name__ == "__main__":
    app()
