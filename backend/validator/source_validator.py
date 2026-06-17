"""Core source validation — stats, drift, missing columns, dtype changes."""

from __future__ import annotations

from typing import Any, Optional

from parser.ast_parser import ASTParser

from .column_expectations import dtype_from_snapshot
from .column_provenance import build_rename_maps_from_nodes, required_columns_for_source
from .file_reader import profile_dataframe, read_source_dataframe
from .findings_generator import generate_findings
from .semantic_matcher import SemanticColumnMatcher
from .snapshot_store import SnapshotStore, snapshot_key


def _normalize_dtype_label(dtype: str) -> str:
    """Canonical dtype labels for snapshot comparison."""
    d = (dtype or "unknown").lower().strip()
    aliases = {
        "str": "string",
        "object": "string",
        "int64": "numeric",
        "float64": "numeric",
        "int32": "numeric",
        "float32": "numeric",
    }
    return aliases.get(d, d)


def _compare_snapshot_columns(
    current_names: set[str],
    current_dtypes: dict[str, str],
    snapshot: Optional[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """additional, missing_vs_snapshot, dtype_changes."""
    if not snapshot:
        return [], [], []

    prev_names = {c["name"] for c in snapshot.get("columns") or []}
    prev_dtypes = {
        c["name"]: _normalize_dtype_label(c.get("dtype", "unknown"))
        for c in snapshot.get("columns") or []
    }
    cur_dtypes = {n: _normalize_dtype_label(current_dtypes.get(n, "unknown")) for n in current_names}

    additional = [
        {"name": n, "dtype": current_dtypes.get(n, "unknown")}
        for n in sorted(current_names - prev_names)
    ]
    missing_snap = [
        {"name": n, "dtype": prev_dtypes.get(n, "unknown")}
        for n in sorted(prev_names - current_names)
    ]
    dtype_changes = []
    for n in sorted(current_names & prev_names):
        old_d = prev_dtypes.get(n, "unknown")
        new_d = cur_dtypes.get(n, "unknown")
        if old_d != new_d:
            dtype_changes.append({
                "column": n,
                "expected_dtype": old_d,
                "new_dtype": new_d,
                "recommended_change": (
                    f"Column '{n}' changed from {old_d} to {new_d}. "
                    f"Consider updating astype or read logic in the pipeline."
                ),
            })
    return additional, missing_snap, dtype_changes


def _compare_snapshot_picklists(
    current_profile: dict,
    snapshot: Optional[dict],
) -> list[dict]:
    """Detect value-level drift in low-cardinality columns.

    Compares current unique values against snapshot baseline and reports
    new values (potential schema/business-rule changes) and retired values.
    """
    if not snapshot:
        return []

    prev_columns = {c["name"]: c for c in snapshot.get("columns") or []}
    drifts = []

    for col_info in current_profile.get("columns", []):
        name = col_info["name"]
        curr_picklist = col_info.get("picklist")
        prev_col = prev_columns.get(name)
        if not curr_picklist or not prev_col:
            continue
        prev_picklist = prev_col.get("picklist")
        if not prev_picklist:
            continue

        curr_values = set(curr_picklist.get("values", []))
        prev_values = set(prev_picklist.get("values", []))

        new_values = sorted(curr_values - prev_values)
        retired_values = sorted(prev_values - curr_values)

        if new_values or retired_values:
            parts = []
            if new_values:
                parts.append(f"new values: {', '.join(new_values[:5])}")
            if retired_values:
                parts.append(f"retired values: {', '.join(retired_values[:5])}")
            msg = f"Column '{name}' picklist drift detected: {'; '.join(parts)}."

            drifts.append({
                "column": name,
                "new_values": new_values,
                "retired_values": retired_values,
                "new_count": len(new_values),
                "retired_count": len(retired_values),
                "severity": "warning" if new_values else "info",
                "message": msg,
            })
    return drifts


def _collect_missing_column_names(
    expected_in_upload: set[str],
    missing_snap: list[dict],
    nodes: list[dict],
    current_names: set[str],
) -> list[str]:
    """Merge code-required, snapshot-drift, and rename-source column names."""
    uploaded_lower = {n.lower(): n for n in current_names}
    missing: list[str] = []

    def _add(name: str) -> None:
        if not name or name in missing:
            return
        if name in current_names:
            return
        if name.lower() in uploaded_lower:
            return
        missing.append(name)

    for exp in sorted(expected_in_upload):
        _add(exp)
    for item in missing_snap:
        _add(item["name"])

    for _nid, rmap in build_rename_maps_from_nodes(nodes).items():
        for old_name, new_name in rmap.items():
            if old_name in current_names or new_name in current_names:
                continue
            if new_name.lower() in uploaded_lower and old_name not in current_names:
                _add(old_name)
            if old_name.lower() in uploaded_lower and new_name not in current_names:
                _add(new_name)

    return missing


def _pipeline_line_for_column(
    col: str,
    provenance_line_numbers: dict[str, int],
    nodes: list[dict],
    source_node_id: str,
) -> Optional[int]:
    if col in provenance_line_numbers:
        return provenance_line_numbers[col]
    node_by_id = {n["id"]: n for n in nodes}
    src = node_by_id.get(source_node_id, {})
    if src.get("line_number"):
        return int(src["line_number"])
    for n in nodes:
        refs = list(n.get("schema_refs") or [])
        if col in refs and n.get("line_number"):
            return int(n["line_number"])
    return None


def _impact_for_missing_column(expected: str, mapped_col: Optional[str]) -> str:
    base = (
        "If claim_date in the target dataset is not mapped correctly, it may result in "
        "null values in the target table. Mapping is required to avoid downstream data quality issues."
    )
    if expected == "claim_date" or expected.endswith("_claim_date"):
        if mapped_col:
            return (
                f"{base} Map uploaded column '{mapped_col}' to '{expected}' before execution."
            )
        return base
    if mapped_col:
        return (
            f"'{expected}' will have NULL values unless mapped to '{mapped_col}'."
        )
    return f"'{expected}' will have NULL values in downstream steps."


async def validate_source_file(
    file_path: str,
    fmt: str,
    source_id: str,
    source_node_id: str,
    pipeline_filename: str,
    code: str,
    nodes: list[dict],
    edges: list[dict],
    *,
    store: Optional[SnapshotStore] = None,
    enable_llm: bool = False,
    filename: str = "",
    all_upload_columns_by_node: Optional[dict[str, list[str]]] = None,
    db: Optional[Session] = None,
    username: Optional[str] = None,
) -> dict[str, Any]:
    from sqlalchemy.orm import Session
    store = store or SnapshotStore()
    key = snapshot_key(pipeline_filename, source_node_id)
    snapshot = store.load(key)

    df = read_source_dataframe(file_path, fmt)
    profile = profile_dataframe(df)
    current_names = set(profile["column_names"])
    current_dtypes = {c["name"]: c["dtype"] for c in profile["columns"]}

    additional, missing_snap, dtype_changes = _compare_snapshot_columns(
        current_names, current_dtypes, snapshot
    )

    # Picklist (value-level) drift detection
    picklist_drifts = _compare_snapshot_picklists(profile, snapshot)

    provenance = required_columns_for_source(
        source_node_id,
        list(current_names),
        nodes,
        edges,
        all_upload_columns_by_node=all_upload_columns_by_node,
    )
    expected_in_upload = provenance.required_in_upload
    column_line_numbers = provenance.column_line_numbers

    missing_columns_raw = _collect_missing_column_names(
        expected_in_upload,
        missing_snap,
        nodes,
        current_names,
    )

    additional_names = [a["name"] for a in additional]
    matcher = SemanticColumnMatcher(enable_llm=enable_llm, code=code, db=db, username=username)
    missing_columns = []
    fuzzy_note = False
    llm_used_match = False

    for exp in missing_columns_raw:
        exp_dtype = dtype_from_snapshot(snapshot, exp)
        recs, used_llm = await matcher.recommend(
            exp,
            exp_dtype,
            additional_names,
            current_dtypes,
            profile.get("sample_data") or [],
        )
        if used_llm:
            llm_used_match = True
        elif not enable_llm and additional_names:
            fuzzy_note = True

        top = recs[0] if recs else None
        mapped_col = top["column"] if top else None
        mapped_dtype = current_dtypes.get(mapped_col, "unknown") if mapped_col else "unknown"
        conf = top["confidence"] if top else 0

        line_no = _pipeline_line_for_column(exp, column_line_numbers, nodes, source_node_id)
        missing_columns.append({
            "expected_name": exp,
            "expected_dtype": exp_dtype,
            "mapped_target_column": mapped_col or "",
            "mapped_target_dtype": mapped_dtype,
            "recommendations": recs,
            "pipeline_line_number": line_no,
            "recommended_pipeline_change": (
                (
                    f"Add or map reference to '{exp}' in pipeline code"
                    + (f" (line {line_no})" if line_no else " near source read.")
                )
                if not mapped_col
                else f"Map uploaded column '{mapped_col}' to expected '{exp}' before execution."
            ),
            "impact_on_target": _impact_for_missing_column(exp, mapped_col),
            "top_confidence": conf,
        })

    kf, ka, llm_findings_used = await generate_findings(
        profile,
        code,
        snapshot,
        additional_count=len(additional),
        missing_count=len(missing_columns),
        dtype_count=len(dtype_changes),
        enable_llm=enable_llm,
        db=db,
        username=username,
    )

    baseline_cols = None
    baseline_col_count = None
    if snapshot:
        snap_columns = snapshot.get("columns") or []
        baseline_cols = [
            {"name": c["name"], "dtype": c.get("dtype", "unknown")}
            for c in snap_columns
        ]
        baseline_col_count = len(snap_columns)

    return {
        "source_id": source_id,
        "node_id": source_node_id,
        "filename": filename or file_path,
        "row_count": profile["row_count"],
        "column_count": profile["column_count"],
        "null_blank_columns": profile["null_blank_columns"],
        "columns": profile["columns"],
        "sample_data": profile["sample_data"],
        "key_findings": kf,
        "key_alerts": ka,
        "additional_columns": additional,
        "missing_columns": missing_columns,
        "dtype_changes": dtype_changes,
        "picklist_drifts": picklist_drifts,
        "has_previous_snapshot": snapshot is not None,
        "baseline_columns": baseline_cols,
        "baseline_column_count": baseline_col_count,
        "llm_used": enable_llm and (llm_findings_used or llm_used_match),
        "fuzzy_fallback_note": fuzzy_note,
    }


async def validate_all_sources(
    code: str,
    pipeline_filename: str,
    saved_paths: dict[str, str],
    sources: list[dict],
    nodes: list[dict],
    edges: list[dict],
    *,
    enable_llm: bool = False,
    file_mapping: Optional[dict[str, str]] = None,
    db: Optional[Session] = None,
    username: Optional[str] = None,
) -> dict[str, Any]:
    from sqlalchemy.orm import Session
    store = SnapshotStore()
    files: dict[str, Any] = {}
    file_mapping = file_mapping or {}

    all_upload_columns_by_node: dict[str, list[str]] = {}
    for s in sources:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        path = saved_paths.get(sid)
        if not path:
            continue
        fmt = s.get("format") or "csv"
        df = read_source_dataframe(path, fmt)
        profile = profile_dataframe(df)
        all_upload_columns_by_node[s["node_id"]] = profile["column_names"]

    for s in sources:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        path = saved_paths.get(sid)
        if not path:
            continue
        logical = file_mapping.get(sid) or s.get("filename") or sid
        result = await validate_source_file(
            path,
            s.get("format") or "csv",
            sid,
            s["node_id"],
            pipeline_filename,
            code,
            nodes,
            edges,
            store=store,
            enable_llm=enable_llm,
            filename=str(logical),
            all_upload_columns_by_node=all_upload_columns_by_node,
            db=db,
            username=username,
        )
        files[sid] = result

    return {"files": files}


def build_snapshot_from_profile(
    pipeline_filename: str,
    source_node_id: str,
    profile: dict,
    column_lineage: Optional[dict] = None,
) -> dict:
    cols = []
    total = profile.get("row_count") or 0
    for c in profile.get("columns") or []:
        cols.append({
            "name": c["name"],
            "dtype": c["dtype"],
            "null_count": c.get("null_count", 0),
            "total_rows": total,
        })
    return {
        "key": snapshot_key(pipeline_filename, source_node_id),
        "columns": cols,
        "row_count": profile.get("row_count", 0),
        "column_count": profile.get("column_count", 0),
        "column_lineage": column_lineage or {},
    }


def persist_snapshots_after_execution(
    pipeline_filename: str,
    sources: list[dict],
    saved_paths: dict[str, str],
    parse_nodes: list[dict],
) -> None:
    """Save upload schema snapshots and source-node column_lineage after successful run."""
    store = SnapshotStore()
    node_by_id = {n["id"]: n for n in parse_nodes}

    for s in sources:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        nid = s["node_id"]
        path = saved_paths.get(sid)
        if not path:
            continue
        fmt = s.get("format") or "csv"
        df = read_source_dataframe(path, fmt)
        profile = profile_dataframe(df)
        lineage = None
        node = node_by_id.get(nid)
        if node and isinstance(node.get("runtime"), dict):
            lineage = node["runtime"].get("column_lineage")
        key = snapshot_key(pipeline_filename, nid)
        if store.exists(key):
            continue
        snap = build_snapshot_from_profile(pipeline_filename, nid, profile, lineage)
        store.save(key, snap)


def parse_and_extract(code: str, *, language: str = "python") -> tuple[list[dict], list[dict], list[dict]]:
    if language == "scala":
        from parser.scala_parser import ScalaSparkParser
        parser = ScalaSparkParser(code)
    elif language == "sql":
        from parser.sql_parser import SparkSQLParser
        parser = SparkSQLParser(code)
    else:
        parser = ASTParser(code)
    result = parser.parse()
    return parser.extract_sources(), result["nodes"], result["edges"]
