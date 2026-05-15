"""Per-source expected column names — delegates to column provenance simulation."""

from __future__ import annotations

from typing import Any, Optional

from .column_provenance import ProvenanceResult, required_columns_for_source


def expected_columns_for_source(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    source_node_id: str,
    upload_columns: Optional[list[str]] = None,
    all_upload_columns_by_node: Optional[dict[str, list[str]]] = None,
) -> set[str]:
    """Return required upload column names for a source (provenance-based)."""
    upload_columns = upload_columns or []
    result: ProvenanceResult = required_columns_for_source(
        source_node_id,
        upload_columns,
        nodes,
        edges,
        all_upload_columns_by_node=all_upload_columns_by_node,
    )
    return result.required_in_upload


def dtype_from_snapshot(snapshot: dict | None, col_name: str) -> str:
    if not snapshot:
        return "unknown"
    for c in snapshot.get("columns") or []:
        if c.get("name") == col_name:
            return c.get("dtype") or "unknown"
    return "unknown"
