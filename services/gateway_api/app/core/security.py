"""Security helpers and redaction utilities (extended in later iterations)."""

from typing import Any

SENSITIVE_KEYS = {"password", "token", "access_token", "authorization", "secret"}


def redact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_KEYS:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted
