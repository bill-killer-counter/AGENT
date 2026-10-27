"""Temporary in-memory memory. C can replace this implementation with SQLite later."""
from __future__ import annotations

from copy import deepcopy
import uuid


class MockMemory:
    def __init__(self):
        self._items = {}

    def save_confirmed(self, workspace_id: str, item: dict) -> dict:
        saved = deepcopy(item)
        saved["memory_id"] = saved.get("memory_id", uuid.uuid4().hex)
        saved["workspace_id"] = workspace_id
        saved["status"] = "confirmed"
        self._items[saved["memory_id"]] = saved
        return deepcopy(saved)

    def list_confirmed(self, workspace_id: str) -> list[dict]:
        return [deepcopy(x) for x in self._items.values() if x["workspace_id"] == workspace_id]

    def delete(self, memory_id: str) -> bool:
        return self._items.pop(memory_id, None) is not None

    def clear(self, workspace_id: str) -> None:
        for key in [k for k, v in self._items.items() if v["workspace_id"] == workspace_id]:
            del self._items[key]
