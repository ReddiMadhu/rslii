"""Orchestrate parse, rewrite, exec, and optional LLM enrichment."""

from __future__ import annotations

import os
import shutil
import json
import subprocess
import sys
import threading
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


def _kill_process_tree(pid: int) -> None:
    import psutil
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
        parent.kill()
    except Exception:
        pass


def _monitor_process(
    proc: subprocess.Popen,
    timeout_sec: float,
    mem_limit_mb: float,
    limit_reached: dict[str, str | None],
) -> None:
    import psutil
    import time

    start_time = time.perf_counter()
    try:
        parent = psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        return

    while proc.poll() is None:
        elapsed = time.perf_counter() - start_time
        if elapsed > timeout_sec:
            limit_reached["type"] = "timeout"
            _kill_process_tree(proc.pid)
            break

        try:
            total_mem = parent.memory_info().rss
            for child in parent.children(recursive=True):
                try:
                    total_mem += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if total_mem > mem_limit_mb * 1024 * 1024:
                limit_reached["type"] = "memory"
                _kill_process_tree(proc.pid)
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        time.sleep(0.1)


def execute_pipeline_sync(
    code: str,
    saved_paths_by_source_id: dict[str, str],
    *,
    session_id: str,
    temp_dir: str,
    sse_callback: Optional[Callable[[str, dict], None]] = None,
    overrides: Optional[dict] = None,
    pipeline_filename: str = "pipeline.py",
) -> dict:
    """
    Run instrumented pipeline in an isolated subprocess with resource limits.

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
    paths_for_exec = dict(saved_paths_by_source_id)
    if overrides:
        from validator.preprocess import apply_overrides_to_uploads

        paths_for_exec = apply_overrides_to_uploads(
            saved_paths_by_source_id,
            sources_meta,
            overrides,
            uploads,
        )

    upload_by_node_id: dict[str, str] = {}
    for s in sources_meta:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        nid = s["node_id"]
        p = paths_for_exec.get(sid)
        if p:
            upload_by_node_id[nid] = p

    rename_maps = extract_rename_maps_from_nodes(nodes, parser.tree)

    instrument_module(parser.tree, parser.injection_steps, upload_by_node_id, output_dir)
    rewritten = unparse_module(parser.tree)

    # Write rewritten_pipeline.py
    rewritten_path = os.path.join(temp_dir, "rewritten_pipeline.py")
    with open(rewritten_path, "w", encoding="utf-8") as f:
        f.write(rewritten)

    # Write config.json
    config = {
        "nodes": nodes,
        "edges": edges,
        "rename_maps": rename_maps,
        "session_id": session_id,
        "temp_dir": temp_dir,
        "warnings": warnings,
        "base_summary": base_summary,
        "pipeline_filename": pipeline_filename,
        "sources_meta": sources_meta,
        "paths_for_exec": paths_for_exec,
    }
    config_path = os.path.join(temp_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, default=str)

    # Prepare command to execute runner_entry.py
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    entry_script = os.path.join(backend_dir, "executor", "runner_entry.py")

    # Spawn subprocess
    process = subprocess.Popen(
        [sys.executable, entry_script, config_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # Line-buffered
        cwd=backend_dir,
    )

    limit_reached = {"type": None}
    monitor_thread = threading.Thread(
        target=_monitor_process,
        args=(process, 30.0, 512.0, limit_reached),
        daemon=True,
    )
    monitor_thread.start()

    non_prefixed_lines = []
    # Read subprocess output line-by-line
    try:
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str.startswith("__RSLI_SSE__:"):
                parts = line_str.split(":", 2)
                if len(parts) == 3:
                    event = parts[1]
                    try:
                        data = json.loads(parts[2])
                        if sse_callback:
                            sse_callback(event, data)
                    except Exception:
                        pass
            else:
                non_prefixed_lines.append(line.rstrip())
    finally:
        process.wait()
        monitor_thread.join()

    # Check why the process exited
    if limit_reached["type"] == "timeout":
        raise TimeoutError("Pipeline execution timed out (limit: 30s)")
    elif limit_reached["type"] == "memory":
        raise MemoryError("Pipeline execution exceeded memory limit (limit: 512MB)")

    if process.returncode != 0:
        err_msg = "\n".join(non_prefixed_lines[-15:])
        if not err_msg:
            err_msg = f"Subprocess exited with return code {process.returncode}"
        raise RuntimeError(err_msg)

    # Read result.json
    result_path = os.path.join(temp_dir, "result.json")
    if not os.path.isfile(result_path):
        raise RuntimeError("Subprocess completed but result.json was not found")

    with open(result_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    return result


def cleanup_temp_dir(temp_dir: str) -> None:
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
