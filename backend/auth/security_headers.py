"""Security headers middleware — adds transport-security and anti-exploit headers.

Injects the following headers on every HTTP response:

    Strict-Transport-Security   — force HTTPS for browsers (HSTS)
    X-Content-Type-Options      — prevent MIME-sniffing
    X-Frame-Options             — clickjacking protection
    X-XSS-Protection            — legacy XSS filter
    Referrer-Policy              — limit referrer leakage
    Content-Security-Policy     — restrict resource loading
    Permissions-Policy          — restrict browser APIs
    Cache-Control               — prevent caching of sensitive responses

Configurable via environment variables:

    RSLI_HSTS_ENABLED       — set to "true" to enable HSTS (default: false in dev)
    RSLI_HSTS_MAX_AGE       — HSTS max-age in seconds (default: 31536000 = 1 year)
    RSLI_HSTS_SUBDOMAINS    — include subdomains in HSTS (default: true)
    RSLI_HSTS_PRELOAD       — add HSTS preload directive (default: false)
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HSTS_ENABLED = os.environ.get("RSLI_HSTS_ENABLED", "false").lower() in ("1", "true", "yes")
HSTS_MAX_AGE = int(os.environ.get("RSLI_HSTS_MAX_AGE", "31536000"))  # 1 year
HSTS_INCLUDE_SUBDOMAINS = os.environ.get("RSLI_HSTS_SUBDOMAINS", "true").lower() in ("1", "true", "yes")
HSTS_PRELOAD = os.environ.get("RSLI_HSTS_PRELOAD", "false").lower() in ("1", "true", "yes")


def _build_hsts_value() -> str:
    """Build the Strict-Transport-Security header value."""
    parts = [f"max-age={HSTS_MAX_AGE}"]
    if HSTS_INCLUDE_SUBDOMAINS:
        parts.append("includeSubDomains")
    if HSTS_PRELOAD:
        parts.append("preload")
    return "; ".join(parts)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every response.

    Follows OWASP Secure Headers Project recommendations.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # --- Transport Security ---
        if HSTS_ENABLED:
            response.headers["Strict-Transport-Security"] = _build_hsts_value()

        # --- Content Security ---
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CSP — restrictive default; allow self and inline styles for the UI
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'"
        )

        # --- Permissions Policy (formerly Feature-Policy) ---
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()"
        )

        # --- Cache Control for API responses ---
        # Don't override if already set (e.g. for file downloads)
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        return response


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_security_headers(app):
    """Attach security headers middleware to a FastAPI app.

    Call this once in main.py after creating the FastAPI application instance.
    """
    app.add_middleware(SecurityHeadersMiddleware)
