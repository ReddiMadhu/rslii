"""RSLI Backend — Python ETL Visual Lineage Analyzer API."""

import ast
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="RSLI API",
    description="Python ETL Visual Lineage Analyzer",
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    """Analyze a Python ETL script."""
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
