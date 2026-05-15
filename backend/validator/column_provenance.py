"""Per-source column provenance simulation for missing-column detection."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProvenanceResult:
    """Columns that must appear in the target source upload."""

    required_in_upload: set[str] = field(default_factory=set)
    derived_columns: set[str] = field(default_factory=set)
    derived_dependencies: dict[str, list[str]] = field(default_factory=dict)
    column_line_numbers: dict[str, int] = field(default_factory=dict)


def required_columns_for_source(
    target_source_node_id: str,
    upload_columns: list[str],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    all_upload_columns_by_node: Optional[dict[str, list[str]]] = None,
    rename_maps_by_node: Optional[dict[str, dict[str, str]]] = None,
) -> ProvenanceResult:
    """
    Simulate column origins through the pipeline and return columns that must
    exist in the target source file (inverse renames applied for upload names).
    """
    all_upload_columns_by_node = all_upload_columns_by_node or {}
    rename_maps_by_node = rename_maps_by_node or build_rename_maps_from_nodes(nodes)

    node_by_id = {n["id"]: n for n in nodes}
    source_node_ids = {n["id"] for n in nodes if n.get("category") == "source"}

    upload_by_source: dict[str, list[str]] = dict(all_upload_columns_by_node)
    upload_by_source.setdefault(target_source_node_id, list(upload_columns))
    for sid in source_node_ids:
        upload_by_source.setdefault(sid, [])

    preds = _predecessors(edges)
    order = _topological_order(nodes, edges)

    column_origin: dict[str, str] = {}
    derived: set[str] = set()
    derived_deps: dict[str, list[str]] = {}
    active_by_var: dict[str, set[str]] = {}
    rename_new_to_old: dict[str, str] = {}

    def _active_cols() -> set[str]:
        out: set[str] = set()
        for s in active_by_var.values():
            out |= s
        return out

    for nid in order:
        node = node_by_id.get(nid)
        if not node:
            continue
        cat = node.get("category", "")
        method = node.get("method", "")
        var_out = (node.get("variable_out") or "").strip()
        refs = list(node.get("schema_refs") or [])

        if cat == "source":
            cols = upload_by_source.get(nid, [])
            if var_out:
                active_by_var[var_out] = set(cols)
                for c in cols:
                    column_origin[c] = nid
            continue

        in_var = _primary_input_var(nid, preds, node_by_id)
        if in_var and in_var in active_by_var:
            active_by_var[var_out] = set(active_by_var[in_var])
        elif var_out:
            active_by_var.setdefault(var_out, set())

        if cat == "join" and method == "merge":
            _apply_merge(nid, edges, active_by_var, column_origin, upload_by_source, var_out)

        if method == "rename":
            rmap = rename_maps_by_node.get(nid, {})
            active = active_by_var.get(var_out, set())
            for old, new in rmap.items():
                rename_new_to_old[new] = old
                if old in column_origin:
                    column_origin[new] = column_origin.pop(old)
                if old in active:
                    active.discard(old)
                    active.add(new)

        if method == "drop":
            for col in refs:
                for v in active_by_var.values():
                    v.discard(col)
                column_origin.pop(col, None)

        if method == "column_assign" and refs:
            new_col = refs[0]
            deps = [r for r in refs[1:] if r and r != new_col]
            existed_before = new_col in column_origin or new_col in _active_cols()
            if len(refs) == 1 and refs[0] == new_col:
                is_new_column = not _is_inplace_transform(node.get("code") or "", new_col)
            else:
                is_new_column = not existed_before

            if is_new_column:
                derived.add(new_col)
                column_origin.pop(new_col, None)
                if deps:
                    derived_deps[new_col] = deps
                if var_out:
                    active_by_var.setdefault(var_out, set()).add(new_col)
                for dep in deps:
                    origin = column_origin.get(dep)
                    if not origin:
                        origin = _origin_for_ref(dep, column_origin, active_by_var)
                    if origin:
                        column_origin[dep] = origin
            else:
                for dep in deps:
                    origin = column_origin.get(dep)
                    if origin:
                        column_origin[dep] = origin

        for ref in _refs_from_code(node.get("code") or ""):
            if ref in derived:
                continue
            origin = column_origin.get(ref) or _origin_for_ref(ref, column_origin, active_by_var)
            if origin:
                column_origin[ref] = origin

        for ref in refs:
            if ref in derived:
                continue
            origin = column_origin.get(ref) or _origin_for_ref(ref, column_origin, active_by_var)
            if origin:
                column_origin[ref] = origin

    required_logical: set[str] = set()
    for col, origin in column_origin.items():
        if origin != target_source_node_id:
            continue
        if col in derived:
            continue
        required_logical.add(col)

    for _dcol, deps in derived_deps.items():
        for dep in deps:
            if dep in derived:
                continue
            orig = column_origin.get(dep)
            if orig == target_source_node_id:
                required_logical.add(dep)
            elif orig is None and dep not in derived:
                required_logical.add(dep)

    required_in_upload: set[str] = set()
    for col in required_logical:
        required_in_upload.add(rename_new_to_old.get(col, col))

    column_line_numbers: dict[str, int] = {}
    source_line = node_by_id.get(target_source_node_id, {}).get("line_number")
    for col in required_in_upload:
        origin_nid = column_origin.get(col) or column_origin.get(
            rename_new_to_old.get(col, col), ""
        )
        if origin_nid == target_source_node_id and source_line:
            column_line_numbers[col] = int(source_line)
            continue
        for n in nodes:
            refs = list(n.get("schema_refs") or []) + _refs_from_code(n.get("code") or "")
            if col in refs or rename_new_to_old.get(col, col) in refs:
                ln = n.get("line_number")
                if ln:
                    column_line_numbers[col] = int(ln)
                    break
        if col not in column_line_numbers and source_line:
            column_line_numbers[col] = int(source_line)

    return ProvenanceResult(
        required_in_upload=required_in_upload,
        derived_columns=derived,
        derived_dependencies=derived_deps,
        column_line_numbers=column_line_numbers,
    )


def build_rename_maps_from_nodes(nodes: list[dict]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for n in nodes:
        if n.get("method") != "rename":
            continue
        code = n.get("code") or ""
        m = re.search(r"columns\s*=\s*\{([^}]+)\}", code)
        if not m:
            continue
        pairs = re.findall(r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']+)["\']', m.group(1))
        if pairs:
            out[n["id"]] = {old: new for old, new in pairs}
    return out


def _apply_merge(
    nid: str,
    edges: list[dict],
    active_by_var: dict[str, set[str]],
    column_origin: dict[str, str],
    upload_by_source: dict[str, list[str]],
    var_out: str,
) -> None:
    merged: set[str] = set()
    for e in edges:
        if e.get("target") != nid:
            continue
        var = e.get("variable") or ""
        src_nid = e.get("source") or ""
        if not var:
            continue
        if var not in active_by_var:
            cols = upload_by_source.get(src_nid, [])
            active_by_var[var] = set(cols)
            for c in cols:
                column_origin[c] = src_nid
        merged |= active_by_var.get(var, set())
    if var_out:
        active_by_var[var_out] = merged


def _origin_for_ref(
    ref: str,
    column_origin: dict[str, str],
    active_by_var: dict[str, set[str]],
) -> str:
    if ref in column_origin:
        return column_origin[ref]
    return ""


def _is_inplace_transform(code: str, col: str) -> bool:
    """True when assign updates an existing column (e.g. to_datetime), not a new literal."""
    if "pd.to_datetime" in code or ".astype(" in code:
        return True
    if not re.search(rf'\[["\']{re.escape(col)}["\']\]\s*=', code):
        return False
    rhs = code.split("=", 1)[-1] if "=" in code else ""
    return bool(re.search(rf'\[["\']{re.escape(col)}["\']\]', rhs))


def _refs_from_code(code: str) -> list[str]:
    refs: list[str] = []
    for m in re.finditer(r'\[["\']([^"\']+)["\']\]', code):
        refs.append(m.group(1))
    for m in re.finditer(r"(?:subset|columns)\s*=\s*\[([^\]]+)\]", code):
        refs.extend(re.findall(r'["\']([^"\']+)["\']', m.group(1)))
    return list(dict.fromkeys(refs))


def _predecessors(edges: list[dict]) -> dict[str, list[str]]:
    preds: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src and tgt:
            preds[tgt].append(src)
    return preds


def _topological_order(nodes: list[dict], edges: list[dict]) -> list[str]:
    preds = _predecessors(edges)
    succ: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.get("source") and e.get("target"):
            succ[e["source"]].append(e["target"])
    ids = {n["id"] for n in nodes}
    indeg = {nid: len(preds.get(nid, [])) for nid in ids}
    q = deque([nid for nid in ids if indeg[nid] == 0])
    order: list[str] = []
    while q:
        nid = q.popleft()
        order.append(nid)
        for t in succ.get(nid, []):
            indeg[t] -= 1
            if indeg[t] == 0:
                q.append(t)
    for n in sorted(nodes, key=lambda x: x.get("line_number") or 0):
        if n["id"] not in order:
            order.append(n["id"])
    return order


def _primary_input_var(nid: str, preds: dict[str, list[str]], node_by_id: dict) -> str:
    ps = preds.get(nid, [])
    if not ps:
        return ""
    return (node_by_id.get(ps[-1], {}).get("variable_out") or "").strip()
