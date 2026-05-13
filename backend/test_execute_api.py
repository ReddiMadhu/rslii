"""Integration test for /api/execute SSE (uses FastAPI TestClient)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


def test_execute_sse_simple_pipeline():
    from main import app

    client = TestClient(app)
    code = (ROOT / "samples" / "simple_pipeline.py").read_text(encoding="utf-8")
    csv_path = ROOT / "samples" / "sample_data" / "inventory_raw.csv"
    csv_bytes = csv_path.read_bytes()

    data = {
        "code": code,
        "filename": "simple_pipeline.py",
        "enable_llm": "false",
        "file_mapping": json.dumps({"source_1": "inventory_raw.csv"}),
    }
    files = {"file_inventory_raw.csv": ("inventory_raw.csv", csv_bytes, "text/csv")}

    with client.stream("POST", "/api/execute", data=data, files=files) as resp:
        assert resp.status_code == 200
        buf = b""
        for chunk in resp.iter_bytes():
            buf += chunk
        text = buf.decode("utf-8", errors="replace")
        assert "event: node_start" in text or "event: node_complete" in text
        assert "event: result" in text
        assert "inventory_clean.parquet" in text


if __name__ == "__main__":
    test_execute_sse_simple_pipeline()
    print("OK test_execute_api")
