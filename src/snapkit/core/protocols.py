from __future__ import annotations

from typing import Protocol

from snapkit.core.entities import UiItem


class ToolboxRepository(Protocol):
    def list_installed(
        self, search: str = "", limit: int = 300, pinned_filter: str = "all"
    ) -> list[UiItem]: ...

    def list_pinned(self, search: str = "", limit: int = 300) -> list[UiItem]: ...

    def list_not_installed(self, search: str = "", limit: int = 300) -> list[UiItem]: ...

    def list_resources(self, resource_type: str, search: str = "", limit: int = 300) -> list[UiItem]: ...
