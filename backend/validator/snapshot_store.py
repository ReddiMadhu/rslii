"""JSON snapshot persistence for upload schema baselines (not executor runtime snapshots)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional


def snapshot_key(pipeline_filename: str, source_node_id: str) -> str:
    return f"{pipeline_filename}::{source_node_id}"


class SnapshotStore:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "snapshots")
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path_for_key(self, key: str) -> str:
        safe = key.replace("::", "__").replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_dir, f"{safe}.json")

    def save(self, key: str, snapshot_dict: dict[str, Any]) -> None:
        data = dict(snapshot_dict)
        data["key"] = key
        data["timestamp"] = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        path = self._path_for_key(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def load(self, key: str) -> Optional[dict[str, Any]]:
        path = self._path_for_key(key)
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def delete(self, key: str) -> None:
        path = self._path_for_key(key)
        if os.path.isfile(path):
            os.remove(path)
