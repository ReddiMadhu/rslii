"""Column-level lineage builder — post-execution pass.

Combines runtime snapshots (ground truth column state at every node) with
AST-inferred metadata (schema_refs, rename maps) to produce per-node
column lineage mappings and a ``discovered_columns`` index for the
frontend dropdown.
"""

from __future__ import annotations

from typing import Any, Optional

from .context import NodeSnapshot


# ---------------------------------------------------------------------------
# Column states observed at runtime
# ---------------------------------------------------------------------------
STATE_INTRODUCED = "introduced"
STATE_PASSTHROUGH = "passthrough"
STATE_DERIVED = "derived"
STATE_RENAMED = "renamed"
STATE_AGGREGATED = "aggregated"
STATE_AGG_DROPPED = "agg_dropped"
STATE_JOINED = "joined"
STATE_DROPPED = "dropped"
STATE_TYPE_CHANGED = "type_changed"
STATE_WRITTEN = "written"


class ColumnLineageBuilder:
    """Build per-node column lineage from runtime snapshots + AST metadata.

    Instantiated after pipeline execution when all ``NodeSnapshot`` objects
    are available.  The :meth:`build` method returns a dict mapping each
    completed ``node_id`` to its column lineage mapping, and
    :meth:`get_discovered_columns` returns the source / output column index.
    """

    def __init__(
        self,
        nodes: list[dict],
        edges: list[dict],
        snapshots: dict[str, NodeSnapshot],
    ):
        self.nodes = nodes
        self.edges = edges
        self.snapshots = snapshots
        # Pre-compute adjacency for predecessor lookups
        self._pred: dict[str, list[str]] = {}
        for e in edges:
            src, tgt = e.get("source", ""), e.get("target", "")
            self._pred.setdefault(tgt, []).append(src)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> dict[str, dict[str, dict]]:
        """Return ``{node_id: {column_name: ColumnMapping}}`` for every
        completed node.
        """
        result: dict[str, dict[str, dict]] = {}
        for node in self.nodes:
            nid = node["id"]
            snap = self.snapshots.get(nid)
            if not snap or snap.status != "completed":
                continue
            result[nid] = self._node_column_lineage(node, snap)
        return result

    def get_discovered_columns(self) -> dict[str, list[dict]]:
        """Columns grouped for the frontend dropdown.

        * **source** – columns present on source (read) nodes
        * **output** – columns present on target (write) nodes
        """
        source_cols: list[dict] = []
        output_cols: list[dict] = []
        seen_source: set[str] = set()
        seen_output: set[str] = set()

        for node in self.nodes:
            snap = self.snapshots.get(node["id"])
            if not snap or snap.status != "completed":
                continue
            cat = node.get("category", "")
            if cat == "source":
                for col in snap.columns_after:
                    if col not in seen_source:
                        source_cols.append({
                            "name": col,
                            "dtype": snap.dtypes_after.get(col, ""),
                            "node_id": node["id"],
                        })
                        seen_source.add(col)
            elif cat == "target":
                for col in snap.columns_after:
                    if col not in seen_output:
                        output_cols.append({
                            "name": col,
                            "dtype": snap.dtypes_after.get(col, ""),
                            "node_id": node["id"],
                        })
                        seen_output.add(col)

        return {"source": source_cols, "output": output_cols}

    # ------------------------------------------------------------------
    # Per-node computation
    # ------------------------------------------------------------------

    def _node_column_lineage(
        self, node: dict, snap: NodeSnapshot
    ) -> dict[str, dict]:
        category = node.get("category", "")
        method = node.get("method", "")
        schema_refs: list[str] = node.get("schema_refs", [])
        is_source = category == "source"

        cols_before = set(snap.columns_before)
        cols_after = set(snap.columns_after)

        renamed_new_to_old = {v: k for k, v in snap.cols_renamed.items()}

        mappings: dict[str, dict] = {}

        # --- Columns present AFTER this operation --------------------------
        for col in snap.columns_after:
            null_count = snap.null_counts.get(col, 0)
            dtype = snap.dtypes_after.get(col, "")

            # Source nodes: ALL columns are introduced (first appearance)
            if is_source:
                mappings[col] = self._entry(
                    STATE_INTRODUCED, [], dtype, null_count,
                )

            elif col in renamed_new_to_old:
                # Renamed column
                old_name = renamed_new_to_old[col]
                mappings[col] = self._entry(
                    STATE_RENAMED, [old_name], dtype, null_count,
                )

            elif col in (snap.cols_joined or []):
                # Brought in via merge / join / concat
                mappings[col] = self._entry(
                    STATE_JOINED, [], dtype, null_count,
                )

            elif col in (snap.cols_derived or []):
                # Derived (computed) column – find source columns from
                # AST schema_refs that existed before this operation.
                source_cols = [
                    r for r in schema_refs
                    if r in cols_before and r != col
                ]
                raw_cs = node.get("column_sources") or {}
                col_src: dict[str, list[str]] = raw_cs if isinstance(raw_cs, dict) else {}
                for c in col_src.get(col, []):
                    if c in cols_before and c != col and c not in source_cols:
                        source_cols.append(c)
                mappings[col] = self._entry(
                    STATE_DERIVED, source_cols, dtype, null_count,
                )

            elif col in cols_before:
                # Column existed before and after
                if category == "aggregation":
                    state = STATE_AGGREGATED
                else:
                    state = STATE_PASSTHROUGH

                # Check for dtype change
                type_info = (snap.cols_transformed or {}).get(col)
                if type_info:
                    state = STATE_TYPE_CHANGED

                mappings[col] = self._entry(
                    state, [col], dtype, null_count,
                )

            else:
                # New column not captured by derived / joined – introduced
                mappings[col] = self._entry(
                    STATE_INTRODUCED, [], dtype, null_count,
                )

        # --- Columns REMOVED at this operation -----------------------------
        for col in snap.cols_removed or []:
            if col in snap.cols_renamed:
                continue  # renamed, not dropped
            dtype_before = snap.dtypes_before.get(col, "")
            if category == "aggregation":
                state = STATE_AGG_DROPPED
            else:
                state = STATE_DROPPED
            mappings[col] = self._entry(state, [col], dtype_before, 0)

        return mappings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _entry(
        state: str,
        from_cols: list[str],
        dtype: str,
        null_count: int,
    ) -> dict:
        return {
            "state": state,
            "from": from_cols,
            "dtype": dtype,
            "null_count": null_count,
        }
