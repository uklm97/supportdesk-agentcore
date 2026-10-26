"""Finds out who the caller is from the Authorization header.

The runtime's CUSTOM_JWT authorizer has ALREADY verified the token's signature, expiry
and client before our code runs, so here we only read the claims. Never use this
function on a token that did not come through the runtime authorizer.
"""

from __future__ import annotations

import base64
import json
from typing import Any


def bearer_token(context: Any) -> str | None:
    headers = getattr(context, "request_headers", None) or {}
    for name, value in headers.items():
        if name.lower() == "authorization" and isinstance(value, str):
            scheme, _, token = value.partition(" ")
            if scheme.lower() == "bearer" and token.strip():
                return token.strip()
    return None


def customer_id_from_token(token: str | None) -> str | None:
    """Return the `sub` claim of a JWT, or None if it cannot be read."""
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, UnicodeDecodeError):
        return None
    sub = claims.get("sub") if isinstance(claims, dict) else None
    return sub if isinstance(sub, str) and sub.strip() else None
