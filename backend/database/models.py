"""SQLAlchemy ORM models for users and audit logs."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.types import JSON

from .db import Base


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_login = Column(DateTime, nullable=True)
    # Stores last N password hashes (JSON array) to prevent reuse
    password_history = Column(JSON, nullable=True, default=list)

    def to_dict(self, include_email: bool = False):
        """Safe serialization — never includes password_hash."""
        d = {
            "id": self.id,
            "username": self.username,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
        if include_email:
            d["email"] = self.email
        return d


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)         # e.g. "script_execute"
    username = Column(String(50), nullable=False)
    session_id = Column(String(20), nullable=True)
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    summary = Column(JSON, nullable=True)                   # event-specific metadata
    script_hash = Column(String(64), nullable=True)         # SHA256
    filename = Column(String(255), nullable=True)
    risk_level = Column(String(10), nullable=True)          # "low", "medium", "high"
    execution_status = Column(String(20), nullable=True)    # "success", "failed", "blocked"
    duration_ms = Column(Float, nullable=True)
    blob_prefix = Column(String(255), nullable=True)        # Azure Blob path prefix

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_username", "username"),
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_risk_level", "risk_level"),
        Index("idx_audit_session_id", "session_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "username": self.username,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "summary": self.summary,
            "script_hash": self.script_hash,
            "filename": self.filename,
            "risk_level": self.risk_level,
            "execution_status": self.execution_status,
            "duration_ms": self.duration_ms,
            "blob_prefix": self.blob_prefix,
        }
