"""Executor smoke test (run from backend/)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    import shutil
    import tempfile
    import uuid

    from executor.runner import execute_pipeline_sync

    code = (ROOT / "samples" / "simple_pipeline.py").read_text(encoding="utf-8")
    csv_path = str(ROOT / "samples" / "sample_data" / "inventory_raw.csv")
    assert os.path.isfile(csv_path), csv_path

    session_id = uuid.uuid4().hex[:10]
    temp_dir = os.path.join(tempfile.gettempdir(), f"rsli_{session_id}")
    up = os.path.join(temp_dir, "uploads")
    os.makedirs(up, exist_ok=True)
    dest = os.path.join(up, "inventory_raw.csv")
    shutil.copy(csv_path, dest)
    saved = {"source_1": dest}

    res = execute_pipeline_sync(code, saved, session_id=session_id, temp_dir=temp_dir)
    assert res["summary"]["status"] == "completed", res["summary"]
    assert res["summary"]["nodes_completed"] >= 4, res["summary"]
    pq = [o for o in res.get("output_files", []) if o["name"].endswith(".parquet")]
    assert pq, res.get("output_files")
    print("OK phase2:", session_id, "nodes_completed=", res["summary"]["nodes_completed"])
    shutil.rmtree(temp_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
