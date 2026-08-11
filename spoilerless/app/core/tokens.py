"""Token generation + hashing — one definition (PROB-09/#68).

Used by the session repository (48-byte session tokens) and the share
repository (32-byte share tokens); previously each module carried its own
byte-identical copy.
"""

from __future__ import annotations

import hashlib
import secrets


def hash_token(raw: str) -> str:
    """SHA-256 hex digest — the persisted form; the raw token is never stored."""
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_token(nbytes: int = 48) -> str:
    """URL-safe random token, ``nbytes`` of entropy (default 48, sessions)."""
    return secrets.token_urlsafe(nbytes)
