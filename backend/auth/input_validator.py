"""Centralized input validation & sanitization utilities.

Provides allowlist-based validators for all user-facing input fields.
Follows OWASP "accept known good" (allowlist) strategy:
  - Every field has explicit constraints (length, pattern, allowed values)
  - Malformed inputs are rejected outright with clear error messages
  - No reliance on blacklists alone

Usage:
    from auth.input_validator import sanitize_string, validate_filename, ...
"""

import os
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Constants — allowlists and constraints
# ---------------------------------------------------------------------------

# Username: alphanumeric, dots, underscores, hyphens (3-50 chars)
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,50}$")

# Email: basic RFC 5322 pattern (stricter than just checking for "@")
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# Filename: alphanumeric, dots, underscores, hyphens, spaces (no path separators)
FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9._\- ()]{1,255}$")

# Session ID: hex characters only (produced by uuid.uuid4().hex[:10])
SESSION_ID_PATTERN = re.compile(r"^[a-fA-F0-9]{1,40}$")

# Invite code: alphanumeric and common separators
INVITE_CODE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")

# Allowed risk levels (allowlist)
ALLOWED_RISK_LEVELS = {"low", "medium", "high", "critical"}

# Allowed execution statuses (allowlist)
ALLOWED_STATUSES = {"success", "failed", "blocked", "running"}

# Allowed export formats (allowlist)
ALLOWED_EXPORT_FORMATS = {"csv", "json"}

# Allowed column journey directions (allowlist)
ALLOWED_DIRECTIONS = {"upstream", "downstream"}

# Maximum lengths for free-text fields
MAX_CODE_LENGTH = 500_000       # ~500KB of source code
MAX_COLUMN_NAME_LENGTH = 255
MAX_QUERY_PARAM_LENGTH = 200


# ---------------------------------------------------------------------------
# Sanitization helpers
# ---------------------------------------------------------------------------

def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    """Strip whitespace, NUL bytes, and enforce max length.

    Returns None if the input is None or empty after stripping.
    """
    if value is None:
        return None
    # Remove NUL bytes and other control characters (keep newlines/tabs for code)
    cleaned = value.replace("\x00", "").strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        return cleaned[:max_length]
    return cleaned


def strip_control_chars(value: str) -> str:
    """Remove all ASCII control characters except newline and tab."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)


# ---------------------------------------------------------------------------
# Field validators — raise ValueError on invalid input
# ---------------------------------------------------------------------------

def validate_username(username: str) -> str:
    """Validate and return a cleaned username."""
    username = username.strip()
    if not username:
        raise ValueError("Username is required")
    if len(username) < 3 or len(username) > 50:
        raise ValueError("Username must be 3-50 characters")
    if not USERNAME_PATTERN.match(username):
        raise ValueError(
            "Username may only contain letters, numbers, dots, underscores, and hyphens"
        )
    return username


def validate_email(email: str) -> str:
    """Validate and return a cleaned email address."""
    email = email.strip().lower()
    if not email:
        raise ValueError("Email is required")
    if len(email) > 255:
        raise ValueError("Email address is too long")
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email address format")
    return email


def validate_invite_code(code: str) -> str:
    """Validate invite code format."""
    code = code.strip()
    if not code:
        raise ValueError("Invite code is required")
    if not INVITE_CODE_PATTERN.match(code):
        raise ValueError("Invite code contains invalid characters")
    return code


def validate_filename(filename: Optional[str], default: str = "pipeline.py") -> str:
    """Validate and sanitize a filename — prevent path traversal."""
    if not filename:
        return default
    # Strip path components (prevent ../../../etc/passwd attacks)
    safe = os.path.basename(filename.strip())
    if not safe:
        return default
    if not FILENAME_PATTERN.match(safe):
        raise ValueError(
            f"Filename '{safe}' contains invalid characters. "
            "Only letters, numbers, dots, underscores, hyphens, spaces, and parentheses are allowed."
        )
    return safe


def validate_session_id(session_id: str) -> str:
    """Validate session ID format — must be hex-only."""
    session_id = session_id.strip()
    if not session_id:
        raise ValueError("Session ID is required")
    if not SESSION_ID_PATTERN.match(session_id):
        raise ValueError("Invalid session ID format")
    return session_id


def validate_code_input(code: str) -> str:
    """Validate and sanitize source code input."""
    if not code or not isinstance(code, str):
        raise ValueError("Code input is required and must be a string")
    code = strip_control_chars(code)
    if not code.strip():
        raise ValueError("Code input cannot be empty")
    if len(code) > MAX_CODE_LENGTH:
        raise ValueError(
            f"Code input ({len(code)} chars) exceeds maximum allowed "
            f"length of {MAX_CODE_LENGTH} characters"
        )
    return code


def validate_direction(direction: str) -> str:
    """Validate column journey direction — must be upstream or downstream."""
    direction = direction.strip().lower()
    if direction not in ALLOWED_DIRECTIONS:
        raise ValueError(
            f"Invalid direction '{direction}'. Must be one of: {', '.join(sorted(ALLOWED_DIRECTIONS))}"
        )
    return direction


def validate_column_name(column: str) -> str:
    """Validate column name."""
    column = column.strip()
    if not column:
        raise ValueError("Column name is required")
    if len(column) > MAX_COLUMN_NAME_LENGTH:
        raise ValueError(f"Column name exceeds maximum length of {MAX_COLUMN_NAME_LENGTH}")
    # Allow alphanumeric, underscores, dots, spaces, brackets (common in dataframes)
    if not re.match(r"^[\w\s.\-\[\]()]+$", column, re.UNICODE):
        raise ValueError("Column name contains invalid characters")
    return column


def validate_risk_level(risk_level: Optional[str]) -> Optional[str]:
    """Validate risk level against allowlist."""
    if not risk_level:
        return None
    risk_level = risk_level.strip().lower()
    if risk_level not in ALLOWED_RISK_LEVELS:
        raise ValueError(
            f"Invalid risk level '{risk_level}'. "
            f"Must be one of: {', '.join(sorted(ALLOWED_RISK_LEVELS))}"
        )
    return risk_level


def validate_status(status: Optional[str]) -> Optional[str]:
    """Validate execution status against allowlist."""
    if not status:
        return None
    status = status.strip().lower()
    if status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(sorted(ALLOWED_STATUSES))}"
        )
    return status


def validate_export_format(fmt: str) -> str:
    """Validate export format against allowlist."""
    fmt = fmt.strip().lower()
    if fmt not in ALLOWED_EXPORT_FORMATS:
        raise ValueError(
            f"Invalid format '{fmt}'. Must be one of: {', '.join(sorted(ALLOWED_EXPORT_FORMATS))}"
        )
    return fmt


def validate_pagination(page: int, page_size: int) -> tuple[int, int]:
    """Validate and clamp pagination parameters."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100  # Prevent excessively large queries
    return page, page_size


def validate_query_param(value: Optional[str], name: str) -> Optional[str]:
    """Validate a generic query parameter — length and basic sanitization."""
    if not value:
        return None
    value = value.strip()
    if len(value) > MAX_QUERY_PARAM_LENGTH:
        raise ValueError(f"Parameter '{name}' exceeds maximum length of {MAX_QUERY_PARAM_LENGTH}")
    # Remove any NUL bytes or suspicious control characters
    value = strip_control_chars(value)
    return value if value else None


def validate_user_id(user_id: int) -> int:
    """Validate user ID is a positive integer."""
    if not isinstance(user_id, int) or user_id < 1:
        raise ValueError("Invalid user ID")
    return user_id
