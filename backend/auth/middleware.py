"""FastAPI auth middleware — extracts user from JWT HttpOnly cookie."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from auth.service import COOKIE_NAME, decode_token, get_user_by_id
from database.db import get_db


class CurrentUser:
    """Resolved user info attached to requests by auth middleware."""

    __slots__ = ("user_id", "username", "is_admin")

    def __init__(self, user_id: int, username: str, is_admin: bool):
        self.user_id = user_id
        self.username = username
        self.is_admin = is_admin


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    """FastAPI dependency — extracts and validates the JWT from the HttpOnly cookie.

    Raises 401 if the cookie is missing, expired, or the user is deactivated.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")
    username = payload.get("sub")
    is_admin = payload.get("is_admin", False)

    if not user_id or not username:
        raise HTTPException(status_code=401, detail="Malformed token")

    # Verify user still exists and is active
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")

    return CurrentUser(user_id=user.id, username=user.username, is_admin=user.is_admin)


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """FastAPI dependency — requires the current user to be an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
