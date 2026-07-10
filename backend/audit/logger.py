"""Audit logger — records metadata audit trails in the database."""

from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.orm import Session
from database.models import AuditLog

def log_event(
    db: Session,
    event_type: str,
    username: str,
    session_id: str = None,
    summary: dict = None,
    script_hash: str = None,
    filename: str = None,
    risk_level: str = None,
    execution_status: str = None,
    duration_ms: float = None,
    blob_prefix: str = None,
) -> AuditLog:
    """Create and persist an audit log entry in the database."""
    try:
        log_entry = AuditLog(
            event_type=event_type,
            username=username,
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            summary=summary or {},
            script_hash=script_hash,
            filename=filename,
            risk_level=risk_level,
            execution_status=execution_status,
            duration_ms=duration_ms,
            blob_prefix=blob_prefix,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        print(f"Error persisting audit log: {e}")
        return None

async def log_llm_call(
    db: Session,
    session_id: Optional[str],
    username: str,
    prompt: Any,
    response_content: Any,
    model_name: str,
    tokens: int = 0,
) -> None:
    """Log an LLM call to the database and upload detail to Blob Storage if enabled."""
    # Ensure prompt and response_content are stringified to prevent TypeErrors on list inputs
    prompt_str = str(prompt) if not isinstance(prompt, str) else prompt
    resp_str = str(response_content) if not isinstance(response_content, str) else response_content

    summary = {
        "model": model_name,
        "tokens": tokens,
        "prompt_snippet": prompt_str[:200] + ("..." if len(prompt_str) > 200 else ""),
        "response_snippet": resp_str[:200] + ("..." if len(resp_str) > 200 else ""),
    }
    
    # 1. Log event in DB
    log_event(
        db,
        event_type="llm_call",
        username=username,
        session_id=session_id,
        summary=summary,
    )
    
    # 2. Archive to Blob
    if session_id:
        try:
            import sys
            main = sys.modules.get("main")
            if main and hasattr(main, "blob_store") and main.blob_store.enabled:
                import uuid
                call_id = f"llm_{uuid.uuid4().hex[:8]}"
                payload = {
                    "prompt": prompt,
                    "response": response_content,
                    "model": model_name,
                    "tokens": tokens,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await main.blob_store.upload_json(session_id, "llm_logs", f"{call_id}.json", payload)
        except Exception as e:
            print(f"Error archiving LLM log to blob storage: {e}")

