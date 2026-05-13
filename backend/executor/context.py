"""Execution context, snapshots, and final API payload assembly."""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Literal, Optional

import pandas as pd


@dataclass
class NodeSnapshot:
    node_id: str
    status: Literal["completed", "failed", "skipped", "not_reached"] = "completed"
    rows_in: Optional[int] = None
    rows_out: Optional[int] = None
    cols_in: Optional[int] = None
    cols_out: Optional[int] = None
    columns_before: list[str] = field(default_factory=list)
    columns_after: list[str] = field(default_factory=list)
    dtypes_before: dict[str, str] = field(default_factory=dict)
    dtypes_after: dict[str, str] = field(default_factory=dict)
    cols_added: list[str] = field(default_factory=list)
    cols_removed: list[str] = field(default_factory=list)
    cols_renamed: dict[str, str] = field(default_factory=dict)
    rows_filtered: int = 0
    duplicates_removed: int = 0
    nulls_handled: int = 0
    null_counts: dict[str, int] = field(default_factory=dict)
    sample_output: list[dict] = field(default_factory=list)
    sample_input: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0
    error: Optional[str] = None

    def to_runtime_dict(self) -> dict:
        d = asdict(self)
        return d


class RSLIContext:
    def __init__(
        self,
        nodes: list[dict],
        edges: list[dict],
        sse_callback: Optional[Callable[[str, dict], None]] = None,
        rename_maps: Optional[dict[str, dict[str, str]]] = None,
    ):
        self.nodes_template = nodes
        self.edges = edges
        self.sse_callback = sse_callback
        self.rename_maps = rename_maps or {}
        self.snapshots: dict[str, NodeSnapshot] = {}
        self.dataframes: dict[str, pd.DataFrame] = {}
        self.current_node_id: Optional[str] = None
        self.step_start: float = time.perf_counter()
        self.execution_order: list[str] = []
        self.total_start: float = time.perf_counter()
        self._failed = False

    def _emit(self, event: str, data: dict) -> None:
        if self.sse_callback:
            self.sse_callback(event, data)

    def start_step(self, node_id: str) -> None:
        self.current_node_id = node_id
        self.step_start = time.perf_counter()
        node = self._node_by_id(node_id)
        total = len(self.nodes_template)
        idx = next((i for i, n in enumerate(self.nodes_template) if n["id"] == node_id), 0)
        self._emit(
            "node_start",
            {
                "node_id": node_id,
                "label": node.get("label", "") if node else "",
                "index": idx + 1,
                "total": total,
            },
        )

    def store_snapshot(self, node_id: str, snapshot: NodeSnapshot, df_copy: pd.DataFrame) -> None:
        self.snapshots[node_id] = snapshot
        self.dataframes[node_id] = df_copy
        self.execution_order.append(node_id)
        self._emit(
            "node_complete",
            {
                "node_id": node_id,
                "rows_in": snapshot.rows_in,
                "rows_out": snapshot.rows_out,
                "cols_in": snapshot.cols_in,
                "cols_out": snapshot.cols_out,
                "duration_ms": snapshot.duration_ms,
            },
        )

    def mark_current_failed(self, error: str) -> None:
        self._failed = True
        nid = self.current_node_id
        if not nid:
            return
        self.snapshots[nid] = NodeSnapshot(
            node_id=nid,
            status="failed",
            error=error,
        )
        self._emit("node_error", {"node_id": nid, "error": error})

    def mark_remaining_not_reached(self) -> None:
        done = set(self.execution_order)
        if self.current_node_id:
            done.add(self.current_node_id)
        for n in self.nodes_template:
            nid = n["id"]
            if nid not in self.snapshots:
                self.snapshots[nid] = NodeSnapshot(node_id=nid, status="not_reached")

    def get_input_node(self, node_id: str) -> Optional[str]:
        for e in self.edges:
            if e.get("target") == node_id:
                return e.get("source")
        return None

    def get_rename_map(self, node_id: str) -> dict[str, str]:
        return dict(self.rename_maps.get(node_id, {}))

    def _node_by_id(self, node_id: str) -> Optional[dict]:
        for n in self.nodes_template:
            if n["id"] == node_id:
                return n
        return None

    def build_final_result(
        self,
        session_id: str,
        temp_dir: str,
        output_files_meta: list[dict],
        warnings: list[dict],
        llm_used: bool,
        base_summary: Optional[dict] = None,
    ) -> dict:
        total_ms = round((time.perf_counter() - self.total_start) * 1000, 2)
        completed = sum(1 for s in self.snapshots.values() if s.status == "completed")
        failed = sum(1 for s in self.snapshots.values() if s.status == "failed")
        skipped = sum(1 for s in self.snapshots.values() if s.status == "skipped")
        not_reached = sum(1 for s in self.snapshots.values() if s.status == "not_reached")

        if failed and completed == 0:
            overall = "failed"
        elif failed or not_reached:
            overall = "partial"
        else:
            overall = "completed"

        nodes_out: list[dict] = []
        for n in self.nodes_template:
            nd = dict(n)
            snap = self.snapshots.get(n["id"])
            if snap:
                nd["status"] = snap.status
                if snap.status == "completed":
                    rt = snap.to_runtime_dict()
                    nd["runtime"] = rt
                elif snap.status == "failed":
                    nd["status"] = "failed"
                    nd["runtime"] = {
                        "error": snap.error,
                        "rows_in": snap.rows_in,
                        "rows_out": snap.rows_out,
                        "duration_ms": snap.duration_ms,
                    }
                elif snap.status == "not_reached":
                    nd["status"] = "not_reached"
            else:
                nd.setdefault("status", "not_reached")
            nodes_out.append(nd)

        agg = self._aggregate_summary_metrics(nodes_out)
        base = dict(base_summary or {})
        summary = {
            "sources": base.get("sources") or [],
            "targets": base.get("targets") or [],
            "metrics": base.get("metrics") or {},
            "total_nodes": base.get("total_nodes", len(nodes_out)),
            "total_lines": base.get("total_lines", 0),
            "pipeline_count": base.get("pipeline_count", 0),
            "warning_count": base.get("warning_count", 0),
            "status": overall,
            "total_duration_ms": total_ms,
            "nodes_completed": completed,
            "nodes_failed": failed,
            "nodes_skipped": skipped,
            "nodes_not_reached": not_reached,
            **agg,
        }

        return {
            "session_id": session_id,
            "summary": summary,
            "llm_used": llm_used,
            "nodes": nodes_out,
            "edges": self.edges,
            "warnings": warnings,
            "output_files": output_files_meta,
        }

    def _aggregate_summary_metrics(self, nodes_out: list[dict]) -> dict:
        total_rows_in = 0
        total_rows_out = 0
        total_cols_added = 0
        total_cols_removed = 0
        total_nulls = 0
        total_filtered = 0
        total_deduped = 0
        first_source_rows: Optional[int] = None
        last_out_rows: Optional[int] = None

        for n in nodes_out:
            rt = n.get("runtime") or {}
            if n.get("category") == "source" and rt.get("rows_out") is not None:
                if first_source_rows is None:
                    first_source_rows = rt["rows_out"]
            if rt.get("rows_out") is not None:
                last_out_rows = rt["rows_out"]
            total_cols_added += len(rt.get("cols_added") or [])
            total_cols_removed += len(rt.get("cols_removed") or [])
            total_nulls += int(rt.get("nulls_handled") or 0)
            total_filtered += int(rt.get("rows_filtered") or 0)
            total_deduped += int(rt.get("duplicates_removed") or 0)

        return {
            "total_rows_in": first_source_rows,
            "total_rows_out": last_out_rows,
            "total_cols_added": total_cols_added,
            "total_cols_removed": total_cols_removed,
            "total_nulls_handled": total_nulls,
            "total_rows_filtered": total_filtered,
            "total_duplicates_removed": total_deduped,
        }


def extract_rename_maps_from_nodes(nodes: list[dict], tree: ast.Module) -> dict[str, dict[str, str]]:
    """Map node_id -> {old: new} for rename() ops from AST."""
    out: dict[str, dict[str, str]] = {}
    for n in nodes:
        if n.get("method") != "rename":
            continue
        line = n.get("line_number")
        if not line:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "rename" and getattr(node, "lineno", None) == line:
                    m = _rename_kwarg_map(node)
                    if m:
                        out[n["id"]] = m
                    break
    return out


def _rename_kwarg_map(call: ast.Call) -> dict[str, str]:
    for kw in call.keywords:
        if kw.arg != "columns":
            continue
        val = kw.value
        if isinstance(val, ast.Dict):
            mp: dict[str, str] = {}
            for k, v in zip(val.keys, val.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                    if isinstance(k.value, str) and isinstance(v.value, str):
                        mp[k.value] = v.value
            return mp
    return {}
