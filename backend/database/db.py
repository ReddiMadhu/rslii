"""SQLAlchemy engine + session factory.

Supports SQLite (dev) and PostgreSQL (prod) via RSLI_DATABASE_URL env var.
Default: sqlite:///rsli.db (created in backend/ directory).
"""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_DATABASE_URL = os.environ.get("RSLI_DATABASE_URL", "sqlite:///rsli.db")


class Base(DeclarativeBase):
    """Declarative base for all RSLI models."""
    pass


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_connect_args = {}
if _DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    _DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    echo=False,
)

# Enable WAL mode for SQLite (better concurrent reads)
if _DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_wal(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (SQLite dev mode). For PostgreSQL use Alembic."""
    Base.metadata.create_all(bind=engine)
