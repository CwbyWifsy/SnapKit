from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ViewId = Literal[
    "local_scan",
    "installed",
    "not_installed",
    "resource_image",
    "resource_video",
    "resource_document",
    "resource_url",
]

ItemKind = Literal["local", "pinned", "wish", "resource"]


@dataclass(slots=True, frozen=True)
class UiItem:
    item_id: int
    title: str
    subtitle: str
    badge: str
    kind: ItemKind
    install_location: str | None = None
    launch_command: str | None = None
    uninstall_command: str | None = None
    download_url: str | None = None
    resource_type: str | None = None
    path: str | None = None
    icon_path: str | None = None
    linked_app_id: int | None = None
    is_pinned: bool = False
