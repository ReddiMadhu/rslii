"""API Rate Limiting — protects against DoS and brute-force attacks.

Uses slowapi (built on top of limits) to enforce per-client request
thresholds on FastAPI endpoints.  Configurable via environment variables:

    RSLI_RATE_LIMIT_DEFAULT   — default limit for all routes   (e.g. "60/minute")
    RSLI_RATE_LIMIT_AUTH      — stricter limit for auth routes  (e.g. "5/minute")
    RSLI_RATE_LIMIT_UPLOAD    — limit for file upload routes    (e.g. "10/minute")
    RSLI_MAX_REQUEST_SIZE_MB  — maximum request body size in MB (default: 10)
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# ---------------------------------------------------------------------------
# Rate limit configuration (overridable via env vars)
# ---------------------------------------------------------------------------
DEFAULT_RATE_LIMIT = os.environ.get("RSLI_RATE_LIMIT_DEFAULT", "60/minute")
AUTH_RATE_LIMIT = os.environ.get("RSLI_RATE_LIMIT_AUTH", "5/minute")
UPLOAD_RATE_LIMIT = os.environ.get("RSLI_RATE_LIMIT_UPLOAD", "10/minute")
ADMIN_RATE_LIMIT = os.environ.get("RSLI_RATE_LIMIT_ADMIN", "30/minute")

# Maximum request body size (in bytes)
MAX_REQUEST_SIZE_MB = int(os.environ.get("RSLI_MAX_REQUEST_SIZE_MB", "10"))
MAX_REQUEST_SIZE_BYTES = MAX_REQUEST_SIZE_MB * 1024 * 1024  # Convert to bytes


# ---------------------------------------------------------------------------
# Limiter instance — keyed by client IP
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# Custom 429 handler
# ---------------------------------------------------------------------------
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Return a clear JSON error when a client exceeds its rate limit."""
    # Extract retry-after from the exception details
    retry_after = getattr(exc, "detail", "Rate limit exceeded")
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": f"Too many requests. {retry_after}",
            "message": "You have exceeded the allowed number of requests. Please wait before trying again.",
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": str(exc.detail) if hasattr(exc, "detail") else DEFAULT_RATE_LIMIT,
        },
    )


# ---------------------------------------------------------------------------
# Request size validation middleware
# ---------------------------------------------------------------------------
class RequestSizeLimitMiddleware:
    """Reject requests whose Content-Length exceeds the configured maximum.

    Also enforces a maximum on query string length to prevent abuse via
    extremely long URL parameters.
    """

    MAX_QUERY_STRING_LENGTH = 2048  # characters

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # --- Validate query string length ---
            query_string = scope.get("query_string", b"")
            if len(query_string) > self.MAX_QUERY_STRING_LENGTH:
                response = JSONResponse(
                    status_code=414,
                    content={
                        "error": "query_string_too_long",
                        "detail": f"Query string exceeds maximum length of {self.MAX_QUERY_STRING_LENGTH} characters.",
                    },
                )
                await response(scope, receive, send)
                return

            # --- Validate Content-Length header ---
            headers = dict(scope.get("headers", []))
            content_length_raw = headers.get(b"content-length")
            if content_length_raw is not None:
                try:
                    content_length = int(content_length_raw)
                    if content_length > MAX_REQUEST_SIZE_BYTES:
                        response = JSONResponse(
                            status_code=413,
                            content={
                                "error": "payload_too_large",
                                "detail": (
                                    f"Request body size ({content_length} bytes) exceeds "
                                    f"the maximum allowed size of {MAX_REQUEST_SIZE_MB} MB."
                                ),
                            },
                        )
                        await response(scope, receive, send)
                        return
                except (ValueError, TypeError):
                    pass  # Malformed Content-Length — let downstream handle it

        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def setup_rate_limiting(app):
    """Attach rate-limiting middleware and error handler to a FastAPI app.

    Call this once in main.py after creating the FastAPI application instance.
    """
    # Register the custom 429 handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Add SlowAPI middleware (must be added before RequestSizeLimitMiddleware
    # so that size checks happen first in the middleware stack)
    app.add_middleware(SlowAPIMiddleware)

    # Add request size enforcement
    app.add_middleware(RequestSizeLimitMiddleware)
