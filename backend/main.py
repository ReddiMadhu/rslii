"""RSLI Backend — Python ETL Visual Lineage Analyzer API."""

import ast
import asyncio
import json
import math
import os
import queue
import tempfile
import threading
import uuid

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="RSLI API",
    description="Python ETL Visual Lineage Analyzer",
    version="0.1.0",
)

# session_id -> temp workspace (contains uploads/ and output/)
_EXEC_SESSIONS: dict[str, str] = {}
_SESSION_CLEANUP_TIMERS: dict[str, threading.Timer] = {}
_SESSION_CLEANUP_DELAY_S = float(os.environ.get("RSLI_SESSION_CLEANUP_S", "1800"))


def _schedule_session_cleanup(session_id: str) -> None:
    """Remove temp workspace after delay so downloads remain valid briefly."""

    def _run() -> None:
        _SESSION_CLEANUP_TIMERS.pop(session_id, None)
        root = _EXEC_SESSIONS.pop(session_id, None)
        if not root:
            return
        try:
            from executor.runner import cleanup_temp_dir

            cleanup_temp_dir(root)
        except Exception:
            pass

    prev = _SESSION_CLEANUP_TIMERS.pop(session_id, None)
    if prev is not None:
        prev.cancel()
    t = threading.Timer(_SESSION_CLEANUP_DELAY_S, _run)
    t.daemon = True
    _SESSION_CLEANUP_TIMERS[session_id] = t
    t.start()

# CORS — dev + optional production (Azure Storage static site, App Service URL, etc.)
_default_cors = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra = os.environ.get("RSLI_CORS_ORIGINS", "")
_extra_list = [x.strip() for x in _extra.split(",") if x.strip()]
_cors_origins = list(dict.fromkeys(_default_cors + _extra_list))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Known ETL indicators to check if a script contains ETL operations
ETL_INDICATORS = {
    # Read operations
    "read_csv", "read_excel", "read_sql", "read_sql_table", "read_sql_query",
    "read_parquet", "read_json", "read_html", "read_clipboard", "read_fwf",
    "read_orc", "read_sas", "read_spss", "read_feather", "read_hdf",
    "read_pickle", "read_xml", "read_stata",
    # Write operations
    "to_csv", "to_sql", "to_parquet", "to_excel", "to_json", "to_html",
    "to_pickle", "to_feather", "to_hdf", "to_xml", "to_stata", "to_orc",
    # Transform operations
    "merge", "join", "concat", "groupby", "pivot_table", "melt", "pivot",
    "dropna", "fillna", "drop_duplicates", "rename", "assign",
}


# --- Request/Response Models ---

class AnalyzeRequest(BaseModel):
    code: str
    filename: Optional[str] = None
    enable_llm: bool = False


class ParseRequest(BaseModel):
    code: str
    filename: Optional[str] = None


class ColumnJourneySummaryRequest(BaseModel):
    column: str
    direction: str  # "upstream" | "downstream"
    trace_nodes: list[dict]
    source_code: str


class HealthResponse(BaseModel):
    status: str


class ValidationError(BaseModel):
    valid: bool
    error: str
    error_type: str  # "syntax" | "too_large" | "no_etl" | "empty"
    line: Optional[int] = None


# --- Helper Functions ---

def validate_python_code(code: str) -> dict:
    """Validate Python code and check for ETL operations."""
    # Check empty
    if not code.strip():
        return {"valid": False, "error": "No code provided", "error_type": "empty"}

    lines = code.strip().splitlines()
    line_count = len(lines)

    # Check size limit
    if line_count > 2000:
        return {
            "valid": False,
            "error": f"File has {line_count} lines — exceeds 2000-line limit",
            "error_type": "too_large",
        }

    # Check syntax
    try:
        ast.parse(code)
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Syntax error at line {e.lineno}: {e.msg}",
            "error_type": "syntax",
            "line": e.lineno,
        }

    # Check for ETL operations (basic text scan)
    code_lower = code.lower()
    has_etl = any(indicator in code_lower for indicator in ETL_INDICATORS)
    if not has_etl:
        return {
            "valid": False,
            "error": "No ETL operations detected in this script",
            "error_type": "no_etl",
        }

    return {"valid": True, "line_count": line_count}


def _json_safe_for_sse(obj: object) -> object:
    """Recursively replace NaN/Inf so JSON is valid for JavaScript JSON.parse (RFC 8259)."""
    try:
        import numpy as np

        if isinstance(obj, np.floating):
            v = float(obj)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
    except ImportError:
        pass
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe_for_sse(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe_for_sse(v) for v in obj]
    return obj


def _sse_bytes(event: str, payload: dict) -> bytes:
    safe = _json_safe_for_sse(payload)
    return f"event: {event}\ndata: {json.dumps(safe, default=str, allow_nan=False)}\n\n".encode("utf-8")


# --- Routes ---

@app.get("/api/health")
async def health_check():
    """Health check endpoint — also reports LLM availability."""
    try:
        from llm.enricher import is_llm_available
        llm_available = is_llm_available()
    except Exception:
        llm_available = False
    return {"status": "ok", "llm_available": llm_available}


@app.post("/api/parse")
async def parse_script(request: ParseRequest):
    """AST-only parse: discovered sources + DAG skeleton (v2 Phase 1)."""
    validation = validate_python_code(request.code)
    if not validation.get("valid"):
        raise HTTPException(
            status_code=422,
            detail=validation.get("error", "Validation failed"),
        )

    try:
        from parser.ast_parser import ASTParser
        from parser.templates import apply_descriptions

        parser = ASTParser(request.code)
        result = parser.parse()
        result["nodes"] = apply_descriptions(result["nodes"])
        sources = parser.extract_sources()
        skeleton = parser.build_parse_skeleton()
        s = result["summary"]
        summary = {
            "total_nodes": s["total_nodes"],
            "total_lines": s["total_lines"],
            "pipeline_count": s["pipeline_count"],
            "metrics": s["metrics"],
            "warning_count": s.get("warning_count", 0),
            "sources": s.get("sources") or [],
            "targets": s.get("targets") or [],
        }
        if request.filename:
            summary["filename"] = request.filename
        return {
            "sources": sources,
            "skeleton": skeleton,
            "nodes": result["nodes"],
            "edges": result["edges"],
            "summary": summary,
            "warnings": result["warnings"],
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    """Full static analysis + optional LLM (v1). For v2 parse-only, use ``POST /api/parse``."""
    # Step 1: Validate
    validation = validate_python_code(request.code)

    if not validation.get("valid"):
        raise HTTPException(
            status_code=422,
            detail=validation.get("error", "Validation failed"),
        )

    line_count = validation["line_count"]

    # Step 2: Parse with AST engine
    try:
        from parser.ast_parser import ASTParser
        from parser.templates import apply_descriptions

        parser = ASTParser(request.code)
        result = parser.parse()

        # Step 3: Apply template descriptions
        result["nodes"] = apply_descriptions(result["nodes"])

        # Step 4: Optional LLM enrichment
        if request.enable_llm:
            try:
                from llm.enricher import enrich_descriptions
                enriched_nodes, llm_used = await enrich_descriptions(
                    result["nodes"], request.code
                )
                result["nodes"] = enriched_nodes
                result["llm_used"] = llm_used
            except Exception as e:
                import traceback
                traceback.print_exc()
                result["warnings"].append({
                    "type": "llm_error",
                    "message": f"LLM enrichment failed: {str(e)}",
                })

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")


async def _parse_upload_form(form) -> tuple[str, str, dict, list[dict], bool]:
    """Shared multipart parsing for validate-sources and execute."""
    code = form.get("code")
    if not code or not isinstance(code, str):
        raise HTTPException(status_code=422, detail="Missing code")
    filename = form.get("filename") or "pipeline.py"
    enable_llm = str(form.get("enable_llm", "false")).lower() in ("1", "true", "yes")
    raw_map = form.get("file_mapping") or "{}"
    try:
        file_mapping = json.loads(raw_map) if isinstance(raw_map, str) else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="file_mapping must be valid JSON")

    validation = validate_python_code(code)
    if not validation.get("valid"):
        raise HTTPException(status_code=422, detail=validation.get("error", "Validation failed"))

    from parser.ast_parser import ASTParser
    from parser.operations import validate_upload_extension

    pre = ASTParser(code)
    pre.parse()
    sources = pre.extract_sources()

    for s in sources:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        logical = file_mapping.get(sid)
        if not logical:
            raise HTTPException(status_code=422, detail=f"Missing file_mapping for {sid}")
        field = f"file_{logical}"
        uf = form.get(field)
        if uf is None:
            raise HTTPException(status_code=422, detail=f"Missing multipart field {field}")
        fname = getattr(uf, "filename", None) or str(logical)
        ok, msg = validate_upload_extension(s["format"], fname)
        if not ok:
            raise HTTPException(status_code=422, detail=msg)

    return code, filename, file_mapping, sources, enable_llm


async def _save_uploads(form, sources: list, file_mapping: dict, uploads_dir: str) -> dict[str, str]:
    os.makedirs(uploads_dir, exist_ok=True)
    saved_paths: dict[str, str] = {}
    for s in sources:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        logical = file_mapping[sid]
        field = f"file_{logical}"
        uf = form.get(field)
        raw = await uf.read()
        dest = os.path.join(uploads_dir, os.path.basename(str(logical)))
        with open(dest, "wb") as f:
            f.write(raw)
        saved_paths[sid] = dest
    return saved_paths


@app.post("/api/validate-sources")
async def validate_sources(request: Request):
    """Validate uploaded source files against pipeline schema and snapshots."""
    form = await request.form()
    code, filename, file_mapping, sources, enable_llm = await _parse_upload_form(form)

    temp_dir = tempfile.mkdtemp(prefix="rsli_val_")
    uploads = os.path.join(temp_dir, "uploads")
    try:
        saved_paths = await _save_uploads(form, sources, file_mapping, uploads)

        from parser.ast_parser import ASTParser
        from validator.source_validator import validate_all_sources

        parser = ASTParser(code)
        result = parser.parse()
        nodes = result["nodes"]
        edges = result["edges"]

        out = await validate_all_sources(
            code,
            filename,
            saved_paths,
            sources,
            nodes,
            edges,
            enable_llm=enable_llm,
            file_mapping=file_mapping,
        )
        return out
    finally:
        try:
            from executor.runner import cleanup_temp_dir

            cleanup_temp_dir(temp_dir)
        except Exception:
            pass


@app.post("/api/execute")
async def execute_pipeline(request: Request):
    """Execute instrumented pipeline; stream SSE then final JSON result."""
    form = await request.form()
    code, filename, file_mapping, sources, enable_llm = await _parse_upload_form(form)

    raw_overrides = form.get("overrides") or "{}"
    try:
        overrides = json.loads(raw_overrides) if isinstance(raw_overrides, str) else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="overrides must be valid JSON")

    async def event_stream():
        q: queue.Queue = queue.Queue()
        done = object()
        result_holder: list = []
        session_id = uuid.uuid4().hex[:10]
        temp_dir = os.path.join(tempfile.gettempdir(), f"rsli_{session_id}")

        def sse_cb(event: str, data: dict) -> None:
            q.put((event, data))

        try:
            uploads = os.path.join(temp_dir, "uploads")
            os.makedirs(uploads, exist_ok=True)

            saved_paths = await _save_uploads(form, sources, file_mapping, uploads)

            _EXEC_SESSIONS[session_id] = temp_dir

            def worker() -> None:
                try:
                    from executor.runner import execute_pipeline_sync

                    res = execute_pipeline_sync(
                        code,
                        saved_paths,
                        session_id=session_id,
                        temp_dir=temp_dir,
                        sse_callback=sse_cb,
                        overrides=overrides or None,
                        pipeline_filename=filename,
                    )
                    result_holder.append(res)
                except Exception as e:
                    result_holder.append({"__error__": str(e)})
                finally:
                    q.put(done)

            threading.Thread(target=worker, daemon=True).start()
            while True:
                item = await asyncio.to_thread(q.get)
                if item is done:
                    break
                ev, data = item
                yield _sse_bytes(ev, data)

            if result_holder and isinstance(result_holder[0], dict) and "__error__" in result_holder[0]:
                yield _sse_bytes(
                    "node_error",
                    {"node_id": "", "error": result_holder[0]["__error__"]},
                )
                yield _sse_bytes(
                    "result",
                    {
                        "session_id": session_id,
                        "summary": {"status": "failed"},
                        "nodes": [],
                        "edges": [],
                        "warnings": [],
                        "output_files": [],
                    },
                )
            else:
                res = result_holder[0] if result_holder else None
                if res and enable_llm:
                    try:
                        from llm.enricher import enrich_descriptions

                        nodes, llm_used = await enrich_descriptions(res["nodes"], code)
                        res["nodes"] = nodes
                        res["llm_used"] = llm_used
                    except Exception:
                        res["llm_used"] = False
                if res:
                    yield _sse_bytes("result", res)
        finally:
            if session_id in _EXEC_SESSIONS:
                _schedule_session_cleanup(session_id)
            elif os.path.isdir(temp_dir):
                try:
                    from executor.runner import cleanup_temp_dir

                    cleanup_temp_dir(temp_dir)
                except Exception:
                    pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/download/{session_id}/{filename}")
async def download_output(session_id: str, filename: str):
    root = _EXEC_SESSIONS.get(session_id)
    if not root:
        raise HTTPException(status_code=404, detail="Unknown session")
    safe = os.path.basename(filename)
    path = os.path.join(root, "output", safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=safe, media_type="application/octet-stream")


@app.post("/api/column-journey-summary")
async def column_journey_summary(request: ColumnJourneySummaryRequest):
    """Generate GenAI or template summaries for a column's journey."""
    from llm.column_journey_enricher import (
        enrich_column_journey,
        generate_template_node_summary,
        generate_template_overall_summary,
    )

    if not request.trace_nodes:
        return {"node_summaries": {}, "overall_summary": "", "llm_used": False}

    # Try LLM first
    try:
        result = await enrich_column_journey(
            request.column,
            request.direction,
            request.trace_nodes,
            request.source_code,
        )
        if result.get("llm_used") and result.get("overall_summary"):
            return result
    except Exception as e:
        import traceback
        traceback.print_exc()

    # Fallback: template-based summaries
    node_summaries = {}
    for tn in request.trace_nodes:
        node_summaries[tn["id"]] = generate_template_node_summary(tn)

    overall = generate_template_overall_summary(
        request.column, request.direction, request.trace_nodes
    )

    return {
        "node_summaries": node_summaries,
        "overall_summary": overall,
        "llm_used": False,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
