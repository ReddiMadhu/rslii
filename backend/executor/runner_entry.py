"""Subprocess entry point for executing instrumented ETL pipelines.

Reads execution config from a JSON file, runs the instrumented script in
an isolated namespace, emits real-time SSE events via stdout, and writes
the final result JSON back to a file.
"""

from __future__ import annotations

import os
import sys
import json
import traceback

# Ensure the backend root is in python path to allow importing modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from executor.context import RSLIContext
from executor.runner import build_namespace

def custom_sse_callback(event: str, data: dict) -> None:
    # Print the prefixed event to stdout for the parent process to capture
    print(f"__RSLI_SSE__:{event}:{json.dumps(data)}", flush=True)

def main():
    if len(sys.argv) < 2:
        print("Usage: runner_entry.py <config_json_path>", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    temp_dir = config["temp_dir"]
    session_id = config["session_id"]
    rewritten_path = os.path.join(temp_dir, "rewritten_pipeline.py")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    ctx = RSLIContext(
        nodes=config["nodes"],
        edges=config["edges"],
        sse_callback=custom_sse_callback,
        rename_maps=config["rename_maps"]
    )

    ns = build_namespace(ctx)
    ns["__name__"] = "__main__"
    ns["__file__"] = rewritten_path

    # Read and compile rewritten code
    try:
        with open(rewritten_path, "r", encoding="utf-8") as f:
            rewritten_code = f.read()
        exec(compile(rewritten_code, rewritten_path, "exec"), ns, ns)
    except Exception as e:
        traceback.print_exc()
        ctx.mark_current_failed(f"{type(e).__name__}: {e}")
        ctx.mark_remaining_not_reached()

    # Normalize CSVs in output_dir
    if os.path.isdir(output_dir):
        try:
            from validator.csv_export import prepare_dataframe_for_csv
            import pandas as pd
            for name in sorted(os.listdir(output_dir)):
                fp = os.path.join(output_dir, name)
                if not os.path.isfile(fp) or not name.lower().endswith(".csv"):
                    continue
                try:
                    out_df = pd.read_csv(fp)
                    prepare_dataframe_for_csv(out_df).to_csv(fp, index=False)
                except Exception:
                    pass
        except ImportError:
            pass

    # Build out_files list
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
        session_id=session_id,
        temp_dir=temp_dir,
        output_files_meta=out_files,
        warnings=config["warnings"],
        llm_used=False,
        base_summary=config["base_summary"],
    )

    # Persist snapshots after execution
    try:
        from validator.source_validator import persist_snapshots_after_execution
        persist_snapshots_after_execution(
            config["pipeline_filename"],
            config["sources_meta"],
            config["paths_for_exec"],
            result.get("nodes") or config["nodes"],
        )
    except Exception:
        traceback.print_exc()

    # Write final result to result.json
    result_path = os.path.join(temp_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, default=str)

    # Emit pipeline_complete event
    s = result["summary"]
    custom_sse_callback(
        "pipeline_complete",
        {
            "total_duration_ms": s.get("total_duration_ms", 0),
            "nodes_completed": s.get("nodes_completed", 0),
            "nodes_failed": s.get("nodes_failed", 0),
            "nodes_skipped": s.get("nodes_skipped", 0),
        }
    )

if __name__ == "__main__":
    main()
