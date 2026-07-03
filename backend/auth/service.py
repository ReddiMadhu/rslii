"""Auth service — registration, login, password hashing, JWT token management."""

import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy.orm import Session

from database.models import User

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("RSLI_SECRET_KEY", "dev-secret-key-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = int(os.environ.get("RSLI_JWT_EXPIRY_DAYS", "7"))
ADMIN_EMAIL = os.environ.get("RSLI_ADMIN_EMAIL", "")
INVITE_CODE = os.environ.get("RSLI_INVITE_CODE", "")

# Number of previous passwords to remember (prevent reuse)
PASSWORD_HISTORY_SIZE = int(os.environ.get("RSLI_PASSWORD_HISTORY_SIZE", "5"))

# Cookie settings
COOKIE_NAME = "rsli_token"
COOKIE_MAX_AGE = JWT_EXPIRY_DAYS * 24 * 60 * 60  # seconds
COOKIE_SECURE = os.environ.get("RSLI_COOKIE_SECURE", "false").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt (12 rounds)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Password policy enforcement
# ---------------------------------------------------------------------------

def validate_password_strength(password: str) -> list[str]:
    """Validate password against complexity requirements.

    Returns a list of failure reasons (empty list = password is strong enough).
    Policy:
        - Minimum 8 characters
        - At least one uppercase letter (A-Z)
        - At least one lowercase letter (a-z)
        - At least one digit (0-9)
        - At least one special character (!@#$%^&*()_+-=[]{}|;':",./<>?~`)
    """
    errors: list[str] = []

    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter (A-Z)")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter (a-z)")
    if not re.search(r"[0-9]", password):
        errors.append("Password must contain at least one number (0-9)")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;':"",./<>?~`]", password):
        errors.append("Password must contain at least one special character")

    return errors


def _check_password_history(plain: str, history: list[str] | None) -> bool:
    """Return True if the password matches any hash in the history."""
    if not history:
        return False
    for old_hash in history:
        try:
            if verify_password(plain, old_hash):
                return True
        except Exception:
            continue
    return False


def _update_password_history(
    current_hash: str, history: list[str] | None
) -> list[str]:
    """Prepend current_hash to history and trim to PASSWORD_HISTORY_SIZE."""
    history = list(history or [])
    history.insert(0, current_hash)
    return history[:PASSWORD_HISTORY_SIZE]


# ---------------------------------------------------------------------------
# JWT token management
# ---------------------------------------------------------------------------

def create_token(user: User) -> str:
    """Create a JWT token for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "user_id": user.id,
        "is_admin": user.is_admin,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns payload dict or None."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ---------------------------------------------------------------------------
# User CRUD operations
# ---------------------------------------------------------------------------

def register_user(
    db: Session, username: str, email: str, password: str, invite_code: str
) -> User:
    """Register a new user. Raises ValueError on validation failure."""
    # Validate invite code
    if not INVITE_CODE:
        raise ValueError("Registration is not configured — RSLI_INVITE_CODE not set")
    if invite_code != INVITE_CODE:
        raise ValueError("Invalid invite code")

    # Validate fields
    username = username.strip()
    email = email.strip().lower()
    if not username or len(username) < 3 or len(username) > 50:
        raise ValueError("Username must be 3-50 characters")
    if not email or "@" not in email:
        raise ValueError("Invalid email address")

    # Enforce strong password policy
    pw_errors = validate_password_strength(password)
    if pw_errors:
        raise ValueError("; ".join(pw_errors))

    # Check uniqueness
    if db.query(User).filter(User.username == username).first():
        raise ValueError("Username already taken")
    if db.query(User).filter(User.email == email).first():
        raise ValueError("Email already registered")

    # Determine admin status
    is_admin = bool(ADMIN_EMAIL and email == ADMIN_EMAIL.strip().lower())

    pw_hash = hash_password(password)
    user = User(
        username=username,
        email=email,
        password_hash=pw_hash,
        is_admin=is_admin,
        password_history=[pw_hash],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Verify credentials and return user, or None if invalid."""
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    return user


def change_password(db: Session, user_id: int, current_password: str, new_password: str):
    """Change a user's password. Raises ValueError on failure."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    if not verify_password(current_password, user.password_hash):
        raise ValueError("Current password is incorrect")

    # Enforce strong password policy
    pw_errors = validate_password_strength(new_password)
    if pw_errors:
        raise ValueError("; ".join(pw_errors))

    # Check password history to prevent reuse
    if _check_password_history(new_password, user.password_history):
        raise ValueError(
            f"Cannot reuse any of your last {PASSWORD_HISTORY_SIZE} passwords"
        )

    new_hash = hash_password(new_password)
    user.password_history = _update_password_history(
        user.password_hash, user.password_history
    )
    user.password_hash = new_hash
    db.commit()


def reset_password(db: Session, admin_user_id: int, target_user_id: int) -> str:
    """Admin resets another user's password. Returns temporary password.

    Generates a password that satisfies the strong password policy.
    """
    import secrets
    import string

    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or not admin.is_admin:
        raise ValueError("Not authorized")
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise ValueError("User not found")
    if target.id == admin.id:
        raise ValueError("Use change-password for your own account")

    # Generate a strong temporary password that satisfies the policy
    # Ensure at least one of each required character type
    upper = secrets.choice(string.ascii_uppercase)
    lower = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    special = secrets.choice("!@#$%^&*()_+-=")
    rest = secrets.token_urlsafe(8)  # 8 more random chars
    temp_password = upper + lower + digit + special + rest

    new_hash = hash_password(temp_password)
    target.password_history = _update_password_history(
        target.password_hash, target.password_history
    )
    target.password_hash = new_hash
    db.commit()
    return temp_password


def set_user_active(db: Session, admin_user_id: int, target_user_id: int, active: bool):
    """Admin activates/deactivates a user."""
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or not admin.is_admin:
        raise ValueError("Not authorized")
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise ValueError("User not found")
    if target.id == admin.id:
        raise ValueError("Cannot deactivate yourself")
    target.is_active = active
    db.commit()


def get_all_users(db: Session) -> list[dict]:
    """Return all users (admin view)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [u.to_dict(include_email=True) for u in users]


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
