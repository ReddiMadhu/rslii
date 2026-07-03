"""SSL/TLS hardening — enforces strong cipher configuration for uvicorn.

Creates a hardened ``ssl.SSLContext`` that:
  • Enforces TLS 1.2 or TLS 1.3 only (disables SSL 2.0, SSL 3.0, TLS 1.0, TLS 1.1)
  • Disables weak ciphers (RC4, DES, 3DES, export, NULL, MD5-based)
  • Enables Forward Secrecy (ECDHE/DHE cipher suites prioritised)
  • Sets secure session and protocol options

Configuration via environment variables:

    RSLI_SSL_CERTFILE  — path to PEM certificate file
    RSLI_SSL_KEYFILE   — path to PEM private key file
    RSLI_SSL_CA_CERTS  — (optional) path to CA bundle for client cert verification
    RSLI_SSL_KEYFILE_PASSWORD — (optional) passphrase for encrypted key files

When RSLI_SSL_CERTFILE is not set the module returns ``None`` so the
application falls back to plain HTTP (suitable for local dev behind a
reverse proxy).
"""

import logging
import os
import ssl
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment-driven paths
# ---------------------------------------------------------------------------
SSL_CERTFILE = os.environ.get("RSLI_SSL_CERTFILE", "")
SSL_KEYFILE = os.environ.get("RSLI_SSL_KEYFILE", "")
SSL_CA_CERTS = os.environ.get("RSLI_SSL_CA_CERTS", "")
SSL_KEYFILE_PASSWORD = os.environ.get("RSLI_SSL_KEYFILE_PASSWORD", "")

# ---------------------------------------------------------------------------
# Strong cipher string — OWASP recommended
# ---------------------------------------------------------------------------
# Prioritise ECDHE for forward secrecy, then DHE.
# Exclude RC4, DES, 3DES, export, NULL, anonymous, and MD5-based ciphers.
STRONG_CIPHERS = ":".join([
    # TLS 1.3 cipher suites are controlled separately by Python and are
    # already strong (TLS_AES_256_GCM_SHA384 etc.) — no need to list them.

    # --- TLS 1.2 ECDHE suites (forward secrecy) ---
    "ECDHE+AESGCM",
    "ECDHE+CHACHA20",
    "ECDHE+AES256",
    "ECDHE+AES128",

    # --- TLS 1.2 DHE suites (forward secrecy, RSA fallback) ---
    "DHE+AESGCM",
    "DHE+CHACHA20",
    "DHE+AES256",
    "DHE+AES128",

    # --- Explicitly exclude weak / broken algorithms ---
    "!aNULL",      # no anonymous ciphers
    "!eNULL",      # no NULL encryption
    "!EXPORT",     # no export-grade ciphers
    "!DES",        # no DES
    "!3DES",       # no Triple DES (Sweet32 attack)
    "!RC4",        # no RC4 (biases)
    "!MD5",        # no MD5 MACs
    "!PSK",        # no pre-shared key (not used here)
    "!SRP",        # no SRP
    "!CAMELLIA",   # uncommon, prefer AES
    "!ARIA",       # uncommon
    "!SEED",       # uncommon
    "!IDEA",       # legacy
    "!DSS",        # no DSA/DSS signing
])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_ssl_context() -> Optional[ssl.SSLContext]:
    """Build a hardened ``ssl.SSLContext`` for uvicorn.

    Returns ``None`` if no certificate is configured (dev mode).
    """
    if not SSL_CERTFILE:
        logger.info(
            "RSLI_SSL_CERTFILE not set — running without TLS. "
            "Use a reverse proxy (nginx / Azure App Gateway) for production TLS."
        )
        return None

    if not os.path.isfile(SSL_CERTFILE):
        raise FileNotFoundError(f"SSL certificate not found: {SSL_CERTFILE}")
    if SSL_KEYFILE and not os.path.isfile(SSL_KEYFILE):
        raise FileNotFoundError(f"SSL private key not found: {SSL_KEYFILE}")

    # Start from PROTOCOL_TLS_SERVER — Python's recommended server context.
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # ── Disable legacy protocols ──
    ctx.options |= ssl.OP_NO_SSLv2       # Disable SSL 2.0
    ctx.options |= ssl.OP_NO_SSLv3       # Disable SSL 3.0 (POODLE)
    ctx.options |= ssl.OP_NO_TLSv1       # Disable TLS 1.0
    ctx.options |= ssl.OP_NO_TLSv1_1     # Disable TLS 1.1

    # ── Only allow TLS 1.2 and TLS 1.3 ──
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    # Allow TLS 1.3 if the platform supports it
    if hasattr(ssl.TLSVersion, "TLSv1_3"):
        ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    else:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2

    # ── Strong cipher configuration ──
    ctx.set_ciphers(STRONG_CIPHERS)

    # ── Additional security options ──
    ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE   # Server chooses cipher
    ctx.options |= ssl.OP_SINGLE_DH_USE              # Fresh DH key per session
    ctx.options |= ssl.OP_SINGLE_ECDH_USE            # Fresh ECDH key per session
    ctx.options |= ssl.OP_NO_COMPRESSION             # Disable TLS compression (CRIME)
    ctx.options |= ssl.OP_NO_TICKET                  # Disable session tickets

    # ── Load certificate and key ──
    password = SSL_KEYFILE_PASSWORD or None
    ctx.load_cert_chain(
        certfile=SSL_CERTFILE,
        keyfile=SSL_KEYFILE or None,
        password=password,
    )

    # ── Optional CA bundle for mutual TLS / client cert verification ──
    if SSL_CA_CERTS and os.path.isfile(SSL_CA_CERTS):
        ctx.load_verify_locations(cafile=SSL_CA_CERTS)
        ctx.verify_mode = ssl.CERT_OPTIONAL
        logger.info("Mutual TLS enabled — client certificates will be verified")

    logger.info(
        "SSL/TLS context created — TLS 1.2+ only, forward secrecy enabled, "
        "weak ciphers disabled"
    )
    return ctx
