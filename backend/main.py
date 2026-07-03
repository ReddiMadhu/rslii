"""RSLI Backend — Python ETL Visual Lineage Analyzer API."""

import ast
import asyncio
from datetime import datetime
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

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from sqlalchemy.orm import Session

from database.db import get_db, init_db
from audit.logger import log_event
from audit.blob_store import BlobAuditStore
from database.models import User, AuditLog

blob_store = BlobAuditStore(os.environ.get("AZURE_STORAGE_CONNECTION_STRING"))
from auth.middleware import get_current_user, require_admin, CurrentUser
from auth.rate_limiter import setup_rate_limiting, limiter, AUTH_RATE_LIMIT, UPLOAD_RATE_LIMIT, ADMIN_RATE_LIMIT
from auth.security_headers import setup_security_headers
from auth.ssl_config import create_ssl_context
from auth.input_validator import (
    sanitize_string, strip_control_chars, validate_code_input,
    validate_column_name, validate_direction, validate_export_format,
    validate_filename, validate_pagination, validate_query_param,
    validate_risk_level, validate_session_id, validate_status,
    validate_user_id, MAX_CODE_LENGTH,
)
from auth.service import (
    register_user,
    authenticate_user,
    change_password,
    reset_password,
    set_user_active,
    get_all_users,
    validate_password_strength,
    COOKIE_NAME,
    COOKIE_MAX_AGE,
    COOKIE_SECURE,
)

app = FastAPI(
    title="RSLI API",
    description="Python ETL Visual Lineage Analyzer",
    version="0.1.0",
)

# --- Rate Limiting & Request Size Enforcement ---
setup_rate_limiting(app)

# --- Security Headers (HSTS, CSP, X-Frame-Options, etc.) ---
setup_security_headers(app)

@app.on_event("startup")
def on_startup():
    init_db()

# --- Auth Request/Response Models ---

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    invite_code: str = Field(..., min_length=1, max_length=100)

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v):
        import re
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9._-]{3,50}$", v):
            raise ValueError("Username may only contain letters, numbers, dots, underscores, and hyphens")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v):
        import re
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email address format")
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


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
    code: str = Field(..., min_length=1, max_length=MAX_CODE_LENGTH)
    filename: Optional[str] = Field(None, max_length=255)
    enable_llm: bool = False

    @field_validator("code")
    @classmethod
    def sanitize_code(cls, v):
        return validate_code_input(v)

    @field_validator("filename")
    @classmethod
    def sanitize_filename(cls, v):
        return validate_filename(v) if v else None


class ParseRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=MAX_CODE_LENGTH)
    filename: Optional[str] = Field(None, max_length=255)

    @field_validator("code")
    @classmethod
    def sanitize_code(cls, v):
        return validate_code_input(v)

    @field_validator("filename")
    @classmethod
    def sanitize_filename(cls, v):
        return validate_filename(v) if v else None


class ColumnJourneySummaryRequest(BaseModel):
    column: str = Field(..., min_length=1, max_length=255)
    direction: str = Field(..., min_length=1, max_length=20)
    trace_nodes: list[dict] = Field(..., max_length=500)
    source_code: str = Field(..., min_length=1, max_length=MAX_CODE_LENGTH)
    session_id: Optional[str] = Field(None, max_length=40)

    @field_validator("column")
    @classmethod
    def sanitize_column(cls, v):
        return validate_column_name(v)

    @field_validator("direction")
    @classmethod
    def validate_dir(cls, v):
        return validate_direction(v)

    @field_validator("source_code")
    @classmethod
    def sanitize_code(cls, v):
        return validate_code_input(v)

    @field_validator("session_id")
    @classmethod
    def sanitize_session_id(cls, v):
        return validate_session_id(v) if v else None


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

@app.post("/api/auth/register")
@limiter.limit(AUTH_RATE_LIMIT)
async def register(request: Request, req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register_user(
            db,
            username=req.username,
            email=req.email,
            password=req.password,
            invite_code=req.invite_code,
        )
        log_event(
            db,
            event_type="user_register",
            username=user.username,
            summary={"email": user.email},
        )
        return {"message": "Account created", "username": user.username}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
@limiter.limit(AUTH_RATE_LIMIT)
async def login(request: Request, req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, username=req.username, password=req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    from auth.service import create_token
    token = create_token(user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )
    log_event(
        db,
        event_type="user_login",
        username=user.username,
        summary={"email": user.email},
    )
    return {"message": "Login successful", "username": user.username, "is_admin": user.is_admin}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Logged out successfully"}


@app.post("/api/auth/validate-password")
async def validate_password_api(request: Request):
    """Public endpoint — validates a password against the policy without storing it.

    Returns the list of unmet requirements so the frontend can show real-time feedback.
    """
    body = await request.json()
    password = body.get("password", "")
    errors = validate_password_strength(password)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "policy": {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digit": True,
            "require_special": True,
        },
    }


@app.get("/api/auth/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "user_id": current_user.user_id,
        "is_admin": current_user.is_admin,
    }


@app.post("/api/auth/change-password")
@limiter.limit(AUTH_RATE_LIMIT)
async def change_user_password(
    request: Request,
    req: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        change_password(
            db,
            user_id=current_user.user_id,
            current_password=req.current_password,
            new_password=req.new_password,
        )
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/admin/users")
async def get_users(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return get_all_users(db)


@app.post("/api/admin/users/{user_id}/reset-password")
@limiter.limit(ADMIN_RATE_LIMIT)
async def reset_user_password(
    request: Request,
    user_id: int,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:
        temp_pw = reset_password(db, admin_user_id=current_user.user_id, target_user_id=user_id)
        return {"temporary_password": temp_pw}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:
        set_user_active(db, admin_user_id=current_user.user_id, target_user_id=user_id, active=False)
        return {"message": "User deactivated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/admin/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:
        set_user_active(db, admin_user_id=current_user.user_id, target_user_id=user_id, active=True)
        return {"message": "User activated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit")
async def get_audit_trail(
    page: int = 1,
    page_size: int = 10,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    username: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # --- Input validation ---
    page, page_size = validate_pagination(page, page_size)
    try:
        username = validate_query_param(username, "username")
        risk_level = validate_risk_level(risk_level)
        status = validate_status(status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    query = db.query(AuditLog)
    
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(AuditLog.timestamp >= df)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601.")
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(AuditLog.timestamp <= dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601.")
            
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if risk_level:
        query = query.filter(AuditLog.risk_level == risk_level)
    if status:
        query = query.filter(AuditLog.execution_status == status)
        
    total = query.count()
    items = query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": [item.to_dict() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/audit/export")
async def export_audit_trail(
    format: str = "csv",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    username: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # --- Input validation ---
    try:
        format = validate_export_format(format)
        username = validate_query_param(username, "username")
        risk_level = validate_risk_level(risk_level)
        status = validate_status(status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    query = db.query(AuditLog)
    
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(AuditLog.timestamp >= df)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601.")
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(AuditLog.timestamp <= dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601.")
            
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if risk_level:
        query = query.filter(AuditLog.risk_level == risk_level)
    if status:
        query = query.filter(AuditLog.execution_status == status)
        
    items = query.order_by(AuditLog.timestamp.desc()).all()
    
    if format == "json":
        import io
        data = [item.to_dict() for item in items]
        bio = io.BytesIO(json.dumps(data, default=str, indent=2).encode("utf-8"))
        return StreamingResponse(
            bio,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=rsli_audit_trail.json"},
        )
    else:
        # Default: CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            "ID", "Event Type", "Username", "Session ID", "Timestamp", 
            "Filename", "Risk Level", "Execution Status", "Duration (ms)", "Summary"
        ])
        
        for item in items:
            writer.writerow([
                item.id,
                item.event_type,
                item.username,
                item.session_id or "",
                item.timestamp.isoformat() if item.timestamp else "",
                item.filename or "",
                item.risk_level or "",
                item.execution_status or "",
                item.duration_ms or "",
                json.dumps(item.summary, default=str)
            ])
            
        bio = io.BytesIO(output.getvalue().encode("utf-8"))
        return StreamingResponse(
            bio,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=rsli_audit_trail.csv"},
        )


@app.get("/api/audit/{log_id}/details")
async def get_audit_details(
    log_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log_entry = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
        
    details = {
        "log": log_entry.to_dict(),
        "files": [],
        "overrides": {},
        "llm_logs": [],
    }
    
    session_id = log_entry.session_id
    if session_id:
        if blob_store.enabled:
            # 1. Fetch file list from Blob
            details["files"] = await blob_store.list_files(session_id, "output_files")
            
            # 2. Fetch overrides from Blob
            overrides_data = await blob_store.download_file(session_id, "overrides", "overrides.json")
            if overrides_data:
                try:
                    details["overrides"] = json.loads(overrides_data.decode("utf-8"))
                except Exception:
                    pass
            
            # 3. Fetch LLM logs from Blob
            llm_files = await blob_store.list_files(session_id, "llm_logs")
            for lf in llm_files:
                lf_data = await blob_store.download_file(session_id, "llm_logs", lf)
                if lf_data:
                    try:
                        details["llm_logs"].append(json.loads(lf_data.decode("utf-8")))
                    except Exception:
                        pass
        else:
            root = _EXEC_SESSIONS.get(session_id)
            if root and os.path.isdir(root):
                out_dir = os.path.join(root, "output")
                if os.path.isdir(out_dir):
                    details["files"] = os.listdir(out_dir)
                
    return details


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
async def parse_script(
    request: ParseRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

        # Run Risk Classifier
        from validator.risk_classifier import RiskClassifier
        classifier = RiskClassifier()
        risk_result = classifier.classify(request.code)

        import hashlib
        script_hash = hashlib.sha256(request.code.encode("utf-8")).hexdigest()

        if risk_result.get("blocked"):
            log_event(
                db,
                event_type="risk_blocked",
                username=current_user.username,
                script_hash=script_hash,
                filename=request.filename or "pipeline.py",
                risk_level=risk_result.get("level"),
                execution_status="blocked",
                summary={"reasons": risk_result.get("reasons")},
            )
        else:
            log_event(
                db,
                event_type="script_parse",
                username=current_user.username,
                script_hash=script_hash,
                filename=request.filename or "pipeline.py",
                risk_level=risk_result.get("level"),
                summary={"total_lines": len(request.code.splitlines())},
            )

        return {
            "sources": sources,
            "skeleton": skeleton,
            "nodes": result["nodes"],
            "edges": result["edges"],
            "summary": summary,
            "warnings": result["warnings"],
            "risk": risk_result,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")


@app.post("/api/analyze")
@limiter.limit(UPLOAD_RATE_LIMIT)
async def analyze(request: Request, req: AnalyzeRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Full static analysis + optional LLM (v1). For v2 parse-only, use ``POST /api/parse``."""
    # Step 1: Validate
    validation = validate_python_code(req.code)

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

        parser = ASTParser(req.code)
        result = parser.parse()

        # Step 3: Apply template descriptions
        result["nodes"] = apply_descriptions(result["nodes"])

        # Step 4: Optional LLM enrichment
        if req.enable_llm:
            try:
                from llm.enricher import enrich_descriptions
                enriched_nodes, llm_used = await enrich_descriptions(
                    result["nodes"], req.code
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
    
    try:
        code = validate_code_input(code)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    raw_filename = form.get("filename")
    try:
        filename = validate_filename(raw_filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    enable_llm = str(form.get("enable_llm", "false")).lower() in ("1", "true", "yes")
    raw_map = form.get("file_mapping") or "{}"
    try:
        file_mapping = json.loads(raw_map) if isinstance(raw_map, str) else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="file_mapping must be valid JSON")

    # Validate file_mapping keys and values to prevent injection
    for k, v in list(file_mapping.items()):
        try:
            # Ensure keys (source ID) and values (logical filename) are safe strings
            validate_column_name(str(k))
            file_mapping[k] = validate_filename(str(v))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid file_mapping: {str(e)}")

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
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit
    for s in sources:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        logical = file_mapping[sid]
        field = f"file_{logical}"
        uf = form.get(field)
        if uf is None:
            raise HTTPException(status_code=422, detail=f"Missing multipart field {field}")
        
        dest = os.path.join(uploads_dir, os.path.basename(str(logical)))
        total_bytes = 0
        
        # Reset file pointer just in case it was read elsewhere
        await uf.seek(0)
        
        with open(dest, "wb") as f:
            while True:
                # Read in chunks of 64KB
                chunk = await uf.read(64 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    f.close()
                    # Clean up the partially written file
                    try:
                        os.remove(dest)
                    except Exception:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"Upload of '{logical}' failed: exceeds maximum file size limit of 50MB"
                    )
                f.write(chunk)
                
        saved_paths[sid] = dest
    return saved_paths


@app.post("/api/validate-sources")
@limiter.limit(UPLOAD_RATE_LIMIT)
async def validate_sources(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
            db=db,
            username=current_user.username,
        )
        return out
    finally:
        try:
            from executor.runner import cleanup_temp_dir

            cleanup_temp_dir(temp_dir)
        except Exception:
            pass


@app.post("/api/execute")
@limiter.limit(UPLOAD_RATE_LIMIT)
async def execute_pipeline(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

            # Log execute request
            import hashlib
            script_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
            log_event(
                db,
                event_type="script_execute",
                username=current_user.username,
                session_id=session_id,
                script_hash=script_hash,
                filename=filename,
                summary={"overrides_applied": overrides},
            )

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
                log_event(
                    db,
                    event_type="execution_complete",
                    username=current_user.username,
                    session_id=session_id,
                    script_hash=script_hash,
                    filename=filename,
                    execution_status="failed",
                    summary={"error": result_holder[0]["__error__"]},
                )
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
                if res:
                    status = res.get("summary", {}).get("status", "success")
                    duration_ms = res.get("summary", {}).get("duration_ms", 0.0)
                    log_event(
                        db,
                        event_type="execution_complete",
                        username=current_user.username,
                        session_id=session_id,
                        script_hash=script_hash,
                        filename=filename,
                        execution_status=status,
                        duration_ms=duration_ms,
                        summary={
                            "total_nodes": len(res.get("nodes", [])),
                            "output_files": res.get("output_files", []),
                        },
                    )
                if res and enable_llm:
                    try:
                        from llm.enricher import enrich_descriptions

                        nodes, llm_used = await enrich_descriptions(
                            res["nodes"], 
                            code, 
                            session_id=session_id,
                            db=db,
                            username=current_user.username
                        )
                        res["nodes"] = nodes
                        res["llm_used"] = llm_used
                    except Exception:
                        res["llm_used"] = False
                if res:
                    yield _sse_bytes("result", res)

            # Archival to Azure Blob Storage
            if blob_store.enabled:
                await blob_store.upload_session_files(session_id, temp_dir, overrides=overrides)
        finally:
            if blob_store.enabled:
                try:
                    from executor.runner import cleanup_temp_dir
                    cleanup_temp_dir(temp_dir)
                except Exception:
                    pass
                _EXEC_SESSIONS.pop(session_id, None)
            else:
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


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
_STATIC_HTM_XLSX = "Claim_Center_ADV_10.1_HTM.xlsx"
_STATIC_HTM_XLSX_PATH = os.path.join(_STATIC_DIR, _STATIC_HTM_XLSX)


@app.get("/api/download/static/claim-center-htm")
async def download_static_htm_output(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve bundled Claim Center HTM Excel (not tied to an execution session)."""
    if not os.path.isfile(_STATIC_HTM_XLSX_PATH):
        raise HTTPException(status_code=404, detail="Static HTM file not found")
    log_event(
        db,
        event_type="file_download",
        username=current_user.username,
        filename=_STATIC_HTM_XLSX,
        summary={"static": True},
    )
    return FileResponse(
        _STATIC_HTM_XLSX_PATH,
        filename=_STATIC_HTM_XLSX,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/download/{session_id}/{filename}")
async def download_output(
    session_id: str,
    filename: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        session_id = validate_session_id(session_id)
        safe = validate_filename(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    root = _EXEC_SESSIONS.get(session_id)
    path = os.path.join(root, "output", safe) if root else ""
    
    # 1. Try local file first
    if path and os.path.isfile(path):
        log_event(
            db,
            event_type="file_download",
            username=current_user.username,
            session_id=session_id,
            filename=safe,
            summary={"storage": "local"},
        )
        return FileResponse(path, filename=safe, media_type="application/octet-stream")
        
    # 2. Fall back to Azure Blob Storage
    if blob_store.enabled:
        data = await blob_store.download_file(session_id, "output_files", safe)
        if data:
            import io
            log_event(
                db,
                event_type="file_download",
                username=current_user.username,
                session_id=session_id,
                filename=safe,
                summary={"storage": "azure_blob"},
            )
            return StreamingResponse(
                io.BytesIO(data),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={safe}"}
            )
            
    raise HTTPException(status_code=404, detail="File not found")


@app.post("/api/column-journey-summary")
async def column_journey_summary(
    request: ColumnJourneySummaryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
            session_id=request.session_id,
            db=db,
            username=current_user.username,
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

    ssl_ctx = create_ssl_context()
    ssl_kwargs = {}
    if ssl_ctx is not None:
        ssl_kwargs["ssl"] = ssl_ctx

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("RSLI_PORT", "8000")),
        reload=os.environ.get("RSLI_RELOAD", "true").lower() in ("1", "true", "yes"),
        **ssl_kwargs,
    )
