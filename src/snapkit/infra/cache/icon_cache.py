from __future__ import annotations

from collections import OrderedDict
from pathlib import Path


class IconCache:
    """Simple in-memory and on-disk cache placeholder for future icon extraction."""

    def __init__(self, max_items: int = 256):
        self._max_items = max_items
        self._memory: OrderedDict[str, bytes] = OrderedDict()

    def get(self, key: str) -> bytes | None:
        value = self._memory.get(key)
        if value is None:
            return None
        self._memory.move_to_end(key)
        return value

    def set(self, key: str, value: bytes):
        self._memory[key] = value
        self._memory.move_to_end(key)
        while len(self._memory) > self._max_items:
            self._memory.popitem(last=False)

    @staticmethod
    def cache_key(path: str | Path, size: int) -> str:
        return f"{Path(path)}::{size}"
