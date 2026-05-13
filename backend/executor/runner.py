"""Orchestrate parse, rewrite, exec, and optional LLM enrichment."""

from __future__ import annotations

import os
import shutil
from typing import Callable, Optional

from parser.ast_parser import ASTParser
from parser.templates import apply_descriptions

from .context import RSLIContext, extract_rename_maps_from_nodes
from .rewriter import instrument_module, unparse_module
from .snapshot import rsli_snapshot_fn


def build_namespace(ctx: RSLIContext) -> dict:
    import csv
    import datetime as dt_mod
    import glob
    import json
    import pathlib
    import re
    import sys

    import numpy as np
    import pandas as pd

    return {
        "__builtins__": __builtins__,
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "_rsli_ctx": ctx,
        "_rsli_snapshot": rsli_snapshot_fn,
        "os": os,
        "sys": sys,
        "json": json,
        "csv": csv,
        "datetime": dt_mod,
        "re": re,
        "glob": glob,
        "pathlib": pathlib,
    }


def execute_pipeline_sync(
    code: str,
    saved_paths_by_source_id: dict[str, str],
    *,
    session_id: str,
    temp_dir: str,
    sse_callback: Optional[Callable[[str, dict], None]] = None,
) -> dict:
    """
    Run instrumented pipeline in an existing workspace directory.

    ``temp_dir`` must contain ``uploads/`` (populated by caller) and will
    receive ``output/``. ``saved_paths_by_source_id`` maps ``source_N`` keys
    to absolute paths under ``uploads/``.
    """
    uploads = os.path.join(temp_dir, "uploads")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    parser = ASTParser(code)
    parse_out = parser.parse()
    parse_out["nodes"] = apply_descriptions(parse_out["nodes"])
    nodes = parse_out["nodes"]
    edges = parse_out["edges"]
    warnings = list(parse_out.get("warnings") or [])
    base_summary = parse_out.get("summary") or {}

    sources_meta = parser.extract_sources()
    upload_by_node_id: dict[str, str] = {}
    for s in sources_meta:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        nid = s["node_id"]
        p = saved_paths_by_source_id.get(sid)
        if p:
            upload_by_node_id[nid] = p

    rename_maps = extract_rename_maps_from_nodes(nodes, parser.tree)

    instrument_module(parser.tree, parser.injection_steps, upload_by_node_id, output_dir)
    rewritten = unparse_module(parser.tree)

    ctx = RSLIContext(nodes, edges, sse_callback=sse_callback, rename_maps=rename_maps)
    ns = build_namespace(ctx)
    ns["__name__"] = "__main__"
    ns["__file__"] = "<rsli_pipeline>"

    try:
        exec(compile(rewritten, "<rsli_pipeline>", "exec"), ns, ns)
    except Exception as e:
        ctx.mark_current_failed(f"{type(e).__name__}: {e}")
        ctx.mark_remaining_not_reached()

    out_files = []
    if os.path.isdir(output_dir):
        for name in sorted(os.listdir(output_dir)):
            fp = os.path.join(output_dir, name)
            if os.path.isfile(fp):
                out_files.append(
                    {
                        "name": name,
                        "download_url": f"/api/download/{session_id}/{name}",
                    }
                )

    result = ctx.build_final_result(
        session_id,
        temp_dir,
        out_files,
        warnings,
        llm_used=False,
        base_summary=base_summary,
    )
    if sse_callback:
        s = result["summary"]
        sse_callback(
            "pipeline_complete",
            {
                "total_duration_ms": s.get("total_duration_ms", 0),
                "nodes_completed": s.get("nodes_completed", 0),
                "nodes_failed": s.get("nodes_failed", 0),
                "nodes_skipped": s.get("nodes_skipped", 0),
            },
        )
    return result


def cleanup_temp_dir(temp_dir: str) -> None:
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
